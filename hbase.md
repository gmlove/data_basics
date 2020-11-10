大数据在线应用支持-hbase
----------

## 环境搭建

```bash
wget https://mirrors.bfsu.edu.cn/apache/hbase/2.3.0/hbase-2.3.0-bin.tar.gz
tar xf hbase-2.3.0-bin.tar.gz
ln -sv hbase-2.3.0-bin hbase

cat > hbase/conf/regionservers <<EOF
hd01-1
hd01-2
EOF

cat > hbase/conf/backup-masters <<EOF
hd01-2
EOF

cat >> hbase/conf/hbase-env.sh <<EOF
export JAVA_HOME=/usr/lib/jvm/java
EOF

cat >> env <<EOF
export HBASE_HOME=/app/hbase
export PATH=\${HBASE_HOME}/bin:\${PATH}
EOF

source ./env
```

修改配置文件：

将`hbase-site.xml`配置内容替换为：

```xml
  <property>
    <name>hbase.cluster.distributed</name>
    <value>true</value>
  </property>
  <property>
    <name>hbase.rootdir</name>
    <value>hdfs://hd01-1:9000/hbase</value>
  </property>

  <property>
    <name>hbase.zookeeper.quorum</name>
    <value>hd01-1</value>
  </property>
  <property>
    <name>hbase.zookeeper.property.dataDir</name>
    <value>/hd/hbase/zookeeper</value>
  </property>
```

启动hbase: `start-hbase.sh`


## 查看进程

在hd01-1上面运行：`jps`和`ssh hd01-2 jps`。可以看到ZK进程HQuorumPeer及HMaster、HRegionServer三个进程在hd01-1上面启动起来了。而HMaster、HRegionServer进程在hd01-2上面启动起来了。

## 基本操作

在hbase中进行一些简单的ddl及dml操作。

安装好hbase之后，运行`hbase shell`进入hbase的命令行窗口，然后执行下述操作：

```
create 'student', 'basic'
list 'student'
describe 'student'
put 'student', 'id1', 'basic:name', 'zhangsan'
put 'student', 'id1', 'basic:gender', 'male'
put 'student', 'id1', 'basic:phone', '18866668888'
put 'student', 'id2', 'basic:name', 'lisi'
put 'student', 'id2', 'basic:gender', 'female'
put 'student', 'id2', 'basic:phone', '18866668888'
scan 'student'
get 'student', 'id1'
disable 'student'
drop 'student'
```

**注意：**hbase shell模式不支持一次性put多个列


## 安装phoenix

```bash
# 由于phonenix暂时不支持hbase-2.3，所以，我们退回到版本1.3.6
wget https://mirrors.bfsu.edu.cn/apache/hbase/hbase-1.3.6/hbase-1.3.6-bin.tar.gz
tar xf hbase-1.3.6-bin.tar.gz
rm -f hbase
ln -sv hbase-1.3.6/ hbase
cp -fv hbase-2.3.0-bin/conf/hbase-site.xml hbase/conf/
cp -fv hbase-2.3.0-bin/conf/hbase-env.xml hbase/conf/
cp -fv hbase-2.3.0-bin/conf/regionservers hbase/conf/
cp -fv hbase-2.3.0-bin/conf/backup-masters hbase/conf/
stop-hbase.sh && rm -rf /hd/hbase/zookeeper && hdfs dfs -rm -r /hbase && start-hbase.sh

wget https:////mirrors.tuna.tsinghua.edu.cn/apache/phoenix/apache-phoenix-4.14.3-HBase-1.3/bin/apache-phoenix-4.14.3-HBase-1.3-bin.tar.gz
tar xf apache-phoenix-4.14.3-HBase-1.3-bin.tar.gz
ln -sv apache-phoenix-4.14.3-HBase-1.3 phoenix
cp phoenix/phoenix-4.14.3-HBase-1.3-client.jar hbase/lib
cp phoenix/phoenix-4.14.3-HBase-1.3-server.jar hbase/lib
```

## phoenix

运行`sqlline.py`，稍等数秒（phoenix正在创建内部表），即可见到熟悉的sql命令行。

运行以下sql，观察结果:

```sql
create table test (mykey integer not null primary key, mycolumn varchar);
upsert into test values (1,'Hello');
upsert into test values (2,'World!');
select * from test;
```

`join`:

```sql
select t.MYKEY, t1.MYKEY, count(*)
from test t
    join test t1 on t.MYKEY=t1.MYKEY
group by t.MYKEY, t1.MYKEY
order by count(*) desc;
```


## FAQ:

运行`sqlline.py`出现错误`phoenix TableNotFoundException: SYSTEM.CATALOG`。phoenix无法创建内部数据表，一般是由于zk数据有问题导致，清空整个数据(`stop-hbase.sh && rm -rf /hd/hbase/zookeeper && hdfs dfs -rm -r /hbase && start-hbase.sh`)，重试即可.














