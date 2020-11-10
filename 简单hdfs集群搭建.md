## hdfs集群

### 规划机器，配置ssh无密码访问

简易集群配置（暂不支持自动高可用，需要zookeeper支持，比较复杂）：

- namenode: 1
- datanode: 2

```bash
docker run -d -h hd01-1 --name hd01-1 -v /hd/app:/app -p 13122:22 brightlgm/centos-ssh
docker run -d -h hd01-2 --name hd01-2 -v /hd/app:/app -p 13222:22 brightlgm/centos-ssh
# 找出两个节点的ip地址，并在对应的hosts文件里面配置相互的ip地址
host1=`docker exec hd01-1 tail -n1 /etc/hosts`
host2=`docker exec hd01-2 tail -n1 /etc/hosts`
docker exec hd01-1 bash -c "echo $host2 >> /etc/hosts"
docker exec hd01-2 bash -c "echo $host1 >> /etc/hosts"

# 分别进入hd01-1和hd01-2，然后ssh对方，以允许host的ssh访问
docker exec -it hd01-1 bash
>> ssh hd01-2
>> ssh hd01-1
```

### 下载安装包，并解压

```bash
# 进入容器
docker exec -it hd01-1 bash

wget https://mirror-hk.koddos.net/apache/hadoop/common/hadoop-3.2.1/hadoop-3.2.1.tar.gz
tar xf hadoop-3.2.1.tar.gz
ln -sv hadoop-3.2.1 hadoop
```

### 配置环境

```bash
cat > env <<EOF
export JAVA_HOME=/usr/lib/jvm/java
export HADOOP_HOME=`pwd`/hadoop
export PATH=\${HADOOP_HOME}/bin:\${HADOOP_HOME}/sbin:\${PATH}
EOF
source ./env
```

### 修改配置文件

修改`core-site.xml`文件`vim hadoop/etc/hadoop/core-site.xml`，加入内容：

```xml
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://hd01-1:9000</value>
    </property>
</configuration>
```

修改`hdfs-site.xml`文件`vim hadoop/etc/hadoop/hdfs-site.xml`，加入内容：

```xml
<configuration>

    <property>
        <name>dfs.replication</name>
        <value>2</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>/hd/data/hdfs/namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>/hd/data/hdfs/datanode</value>
    </property>

</configuration>
```

修改`etc/hadoop/workers`文件，加入：

```
hd01-1
hd01-2
```

创建数据目录：

```bash
# 进入hd01-1: docker exec -it hd01-1 bash
mkdir -pv /app/data/hd01-1/ /app/data/hd01-2/
ln -sv /app/data/hd01-1/ /hd
ssh hd01-2 ln -sv /app/data/hd01-2/ /hd
```

增加公共hadoop变量`vim hadoop/etc/hadoop/hadoop-env.sh`:

```bash
export JAVA_HOME=/usr/lib/jvm/java
export JSVC_HOME=/usr/bin
export HDFS_DATANODE_SECURE_USER=root
export HDFS_SECONDARYNAMENODE_USER=root
export HDFS_NAMENODE_USER=root
export HADOOP_SHELL_EXECNAME=root
```

### 启动dfs并进行验证

```bash
# 格式化namenode
hdfs namenode -format
start-dfs.sh
hdfs dfs -mkdir /test
hdfs dfs -put hadoop/README.txt /test/
hdfs dfs -tail /test/README.txt
```

至此，集群搭建完毕。可以通过`jps`查看启动的进程，将发现这样几个进程：

```
3697 NameNode
3826 DataNode
4675 Jps
4087 SecondaryNameNode
```

在另一个节点查看进程`ssh hd01-2 jps`， 将只能看到一个datanode进程：

```
395 Jps
317 DataNode
```


## 验证集群停止某个datanode，数据依然可以访问

kill某个datanode，再用`hdfs dfs -tail /test/README.txt`查看数据


## 验证删除某个datanode的数据，数据依然可以访问

直接删除某个datanode的文件，再用`hdfs dfs -tail /test/README.txt`查看数据










