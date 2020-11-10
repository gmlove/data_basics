lambda架构
--------

## 需求

应用将打印用户登录日志到日志文件中。实现一套系统，它可以实时获取打印的日志，完成：
- 实时统计当天总登录次数，独立登录人数
- 按天统计当天的总登录次数，独立登录人数

## 方案

1. kafka connect实时从日志中获取数据，写入到一个topic中
2. kafka streaming实时计算统计数据
3. 通过kafka connect实时将数据写入到一张hive表中
4. 每天定时计算统计hive表中的数据，写入hbase等待客户端查询

### 实现

由于kafka的hdfs sink有版本的要求，不便于演示，我们这里使用一个替代方案：
- 将hdfs挂载为nfs
- 用file sink将kafka里面的数据写入到挂载的nfs的一个目录中

**配置hdfs的nfs服务：**

停止hadoop服务：`stop-all.sh`

修改配置文件`hdfs-site.xml`，加入配置：

```xml
<property>
  <name>hadoop.proxyuser.hd01-1.hosts</name>
  <value>*</value>
</property>
```

修改配置文件`core-site.xml`，加入配置：
```xml
<property>
  <name>hadoop.proxyuser.root.groups</name>
  <value>root</value>
</property>
<property>
  <name>hadoop.proxyuser.root.hosts</name>
  <value>*</value>
</property>
```

启动hadoop服务及nfs服务：`start-all.sh && hdfs --daemon start nfs3 && hdfs --daemon start portmap`

**启动kafka connector**

为了节省资源，先停止集群模式的`kafka`，启动hbase，并将hbase的zookeeper用作kafka的zookeeper.

```bash
stop-hbase.sh && rm -rf /hd/hbase/zookeeper && hdfs dfs -rm -r /hbase # 清空已有的hbase数据，防止脏数据引起的错误
rm -f hbase && ln -sv hbase-2.3.0 hbase && start-hbase.sh # 切换版本为2.3.0
rm -rf /tmp/kafka-logs* # 防止kafka读取之前的zk数据而启动失败
bin/kafka-server-start.sh config/server.properties &
```

1. 启动一个用于进行同步的容器`docker run -d -h hd01-3 --name hd01-3 --privileged -v /hd/app:/app -p 13322:22 brightlgm/centos-ssh`

2. 进入容器`docker exec -it hd01-3 bash`，将hd01-1的host加入到/etc/hosts文件中

3. 挂载nfs`mkdir /app/data/hdfs_nfs && mount -t nfs -o vers=3,proto=tcp,nolock,noacl,sync hd01-1:/  /app/data/hdfs_nfs/`

4. 配置并启动hdfs connector:

```bash
# on hd01-3
cd kafka
cat > config/userlogin-source.properties <<EOF
name=local-file-source
connector.class=FileStreamSource
tasks.max=1
file=userlogin.log
topic=userlogin
EOF
cat > config/userlogin-sink-hdfs.properties <<EOF
name=local-file-sink
connector.class=FileStreamSink
tasks.max=1
file=/app/data/hdfs_nfs/tmp/userlogin.csv/userlogin.csv
topics=userlogin
EOF
sed 's/bootstrap.servers=localhost:9092/bootstrap.servers=hd01-1:9092/g' config/connect-standalone.properties > config/userlogin-standalone.properties

bin/connect-standalone.sh config/userlogin-standalone.properties config/userlogin-source.properties config/userlogin-sink-hdfs.properties
```

5. 向userlogin.log文件中随机写入用户登录信息`echo user1, 2020-08-05 $(date '+%H:%M:%S') >> userlogin.log`

6. 使用命令`hdfs dfs -cat /tmp/userlogin.csv/userlogin.csv`查看hdfs中的文件，将发现文件一直在更新，与`userlogin.log`文件中的内容保持一致

**离线统计数据并写入到hbase中**

用hive写入数据到hbase表格，以便应用可以实时查询：

运行`hive`, 在hive中执行以下sql:

```sql
create table if not exists user_login(
    name String,
    login_at Date)
    ROW FORMAT DELIMITED
    FIELDS TERMINATED BY ','
    STORED AS TEXTFILE
    LOCATION 'hdfs://hd01-1:9000/tmp/userlogin.csv';

CREATE TABLE user_login_stat(
  key String,
  value String
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.hbase.HBaseSerDe'
STORED BY 'org.apache.hadoop.hive.hbase.HBaseStorageHandler'
WITH SERDEPROPERTIES (
  'hbase.columns.mapping'=':key,stat:value',
  'serialization.format'='1'
)
TBLPROPERTIES (
  'hbase.table.name'='user_login_stat'
);

insert into user_login_stat select 'total_user_login/2020-08-04', count(*) from user_login where login_at='2020-08-04';
insert into user_login_stat select 'total_user_login/2020-08-05', count(*) from user_login where login_at='2020-08-05';
insert into user_login_stat select 'unique_user_login/2020-08-04', count(distinct name) from user_login where login_at='2020-08-04';
insert into user_login_stat select 'unique_user_login/2020-08-05', count(distinct name) from user_login where login_at='2020-08-05';
```

在hbase中查看数据:

- 运行`hbase shell`
- 输入`list`将能看到由hive创建的hbase表`user_login_stat`
- 输入`scan 'user_login_stat'`即可看到前面写入的数据

上述hive的任务，我们只需要配置为定期运行即可实现每天生成统计数据

**实时统计数据并写入kafka的一个topic，以便可以实时通知客户端**

这里我们首先要编写一个kafka streaming应用来进行数据统计。使用java代码实现，核心代码如下：

```java
final StreamsBuilder builder = new StreamsBuilder();
final KStream<String, String> textLines = builder.stream(inputTopic);

final KStream<String, String> loginUserIdsInToday = textLines
        .filter((key, log) -> UserLogin.isInRequiredFormat(log))
        .filter((key, log) -> UserLogin.isFromDate(log, dateFormat.format(dateService.today())));
final KTable<String, Long> totalUserLoginCount = loginUserIdsInToday
        .groupBy((key, log) -> "total_user_login/" + UserLogin.loginDate(log))
        .count();
final KTable<String, Long> uniqueLoginUsers = loginUserIdsInToday
        .groupBy((key, log) -> "user_login/" + UserLogin.userId(log) + "/" + UserLogin.loginDate(log))
        .count()
        .toStream()
        .filter((key, count) -> count == 1)
        .groupBy((key, count) -> "unique_user_login/" + key.split("/")[2])
        .count();
totalUserLoginCount.toStream()
        // We have to convert the result values to string in order for kafka-console-consumer to display the result correctly, since it just reads the value as string
        .map((key, value) -> new KeyValue<>("", String.format("key=%s, value=%s", key, value)))
        .to(outputTopic, Produced.with(Serdes.String(), Serdes.String()));
uniqueLoginUsers.toStream()
        .map((key, value) -> new KeyValue<>("", String.format("key=%s, value=%s", key, value)))
        .to(outputTopic, Produced.with(Serdes.String(), Serdes.String()));
```

完整代码可以在[这里](https://github.com/gmlove/kafka-streaming-demo/blob/master/src/main/java/test/userlogin/TotalLoginUsers.java)找到。

上面的实现借助了一个基于本地持久化的KTable组件，可以保存应用状态，即便程序失败，也能快速恢复。

将上述应用打包为一个jar包，然后上传到服务器`mvn package && scp target/userlogin-examples-1.0-SNAPSHOT.jar rhd02-1:/app/kafka`

运行此kafka应用`java -cp libs/*:userlogin-examples-1.0-SNAPSHOT.jar test.userlogin.TotalLoginUsers localhost:9092 userlogin userlogin-stat`

然后打开新窗口运行`kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic userlogin-stat`以监控统计到的数据

此时可以观察到，一旦我们运行`echo user1, $(date '+%Y-%m-%d %H:%M:%S') >> /app/kafka/userlogin.log`，刚刚的窗口中将输出总登录用户数和独立登录用户数。

至此，我们这一套架构既可以支持实时的数据统计也可以支持批处理式的数据统计。

这里只是演示了一个简单的统计应用，实际上我们完全可以扩展这里的场景。比如，如果我们的场景是实现推荐系统，那么可以实时的捕捉用户的行为信息，然后根据这些信息去实时优化推荐模型，这就可以带来更好的推荐用户体验了。

## 总结

这一套lambda架构在各大互联网公司里面被广泛用于各类数据应用中，实践证明其可以很容易的支持超大规模的数据量和比较严格的实时性需求。

可能有人已经注意到了，这一套架构的问题在于，对于某个数据应用，我们需要实现两套代码。一套用于实时数据处理，一套用于离线数据处理。那么有没有可能将它们合并起来呢？这就是我们经常提到的kappa架构了，这一套架构试图将流式处理和批处理统一起来。这套架构的一个重要支撑组件就是flink。flink是近几年非常前沿的技术，各大互联网公司都投入了很多精力去研究。阿里甚至基于flink做了很多增强，发展为blink开源项目。

flink背后的设计思路是批处理是流式处理的特例，因此流式处理可以完全支持批处理的场景。flink其实是跟kafka streaming比较类似的一个组件，但是它提供了更多的状态管理能力，更丰富和易于使用的接口。比如我们上面在实现独立登录用户数的时候，使用kafka的api就不是特别方便，而用flink，其实现会更为简单。

由于时间关系，这里就不多介绍了。有兴趣的同学们可以自己去了解。







