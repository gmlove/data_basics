NameNode高可用
--------------

首先，安装必备软件`yum install psmisc` （包含需要用到的fuser命令）

## NameNode工作机制

### 查看NameNode的文件结构

```
[root@hd01-1 app]# tree data/hd01-1/data/hdfs/namenode/
data/hd01-1/data/hdfs/namenode/
|-- current
|   |-- VERSION
|   |-- edits_0000000000000000001-0000000000000000002
|   |-- edits_0000000000000000003-0000000000000000003
|   |-- edits...
|   |-- edits_inprogress_0000000000000000145
|   |-- fsimage_0000000000000000142
|   |-- fsimage_0000000000000000142.md5
|   |-- fsimage_0000000000000000144
|   |-- fsimage_0000000000000000144.md5
|   `-- seen_txid
`-- in_use.lock
```

### 读取fsimage的内容

```bash
# 输出文件描述内容
hdfs oiv -p Delimited -t temporaryDir -i data/hd01-1/data/hdfs/namenode/current/fsimage_0000000000000000142

# 用fsimage启动一个webhdfs
hdfs oiv -i data/hd01-1/data/hdfs/namenode/current/fsimage_0000000000000000142
# 查看webhdfs的内容
hdfs dfs -ls webhdfs://127.0.0.1:5978/
hdfs dfs -ls webhdfs://127.0.0.1:5978/test

# 还可以使用 FileDistribution 分析文件大小进行展示
hdfs oiv -p FileDistribution -maxSize 1024 -step 10 -format -i data/hd01-1/data/hdfs/namenode/current/fsimage_0000000000000000142
```

### 读取edits文件内容

```bash
# 读取成xml格式
hdfs oev -i data/hd01-1/data/hdfs/namenode/current/edits_0000000000000000001-0000000000000000002 -o edits.xml
cat edits.xml

# 读取统计信息
hdfs oev -p stats -i data/hd01-1/data/hdfs/namenode/current/edits_0000000000000000001-0000000000000000002 -o edits.stats
cat edits.stats
```

## NameNode手动高可用(NFS)

1. 先停止现有的服务：`stop-dfs.sh`

2. 配置并初始化共享目录：

```bash
mkdir /app/data/shared
ln -sv /app/data/shared/ /hd/shared
ssh hd01-2 'ln -sv /app/data/shared/ /hd/shared'
```

3. 修改`core-site.xml`：

```xml
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://mycluster</value>
    </property>
```

4. 修改`hdfs-site.xml`，加入配置：

```xml
    <property>
      <name>dfs.nameservices</name>
      <value>mycluster</value>
    </property>
    <property>
      <name>dfs.ha.namenodes.mycluster</name>
      <value>nn1,nn2</value>
    </property>

    <property>
      <name>dfs.namenode.rpc-address.mycluster.nn1</name>
      <value>hd01-1:8020</value>
    </property>
    <property>
      <name>dfs.namenode.rpc-address.mycluster.nn2</name>
      <value>hd01-2:8020</value>
    </property>
    <property>
      <name>dfs.namenode.http-address.mycluster.nn1</name>
      <value>hd01-1:9870</value>
    </property>
    <property>
      <name>dfs.namenode.http-address.mycluster.nn2</name>
      <value>hd01-2:9870</value>
    </property>

    <property>
      <!-- 用于保持Standby NN与Active NN的数据同步，必须是一个共享的目录，可以使用NFS实现。集群的高可用取决于这个目录的高可用，需要使用一些高可用机制，比如冗余的存储 -->
      <name>dfs.namenode.shared.edits.dir</name>
      <value>file:///hd/shared/edits</value>
    </property>

    <property>
      <!-- 同时请求所有NN来决定哪个是Active NN，可以配置为其他实现，如ConfiguredFailoverProxyProvider -->
      <name>dfs.client.failover.proxy.provider.mycluster</name>
      <value>org.apache.hadoop.hdfs.server.namenode.ha.RequestHedgingProxyProvider</value>
    </property>

    <property>
      <!-- failover的时候用于杀掉原有的Active NN，避免脑裂问题 -->
      <name>dfs.ha.fencing.methods</name>
      <value>sshfence</value>
    </property>
    <property>
      <name>dfs.ha.fencing.ssh.private-key-files</name>
      <value>/root/.ssh/id_rsa</value>
    </property>
```

5. 初始化NN2（需要在hd01-2上面执行）: `ssh hd01-2 bash -c "cd /app && source ./env && hdfs namenode -bootstrapStandby"`

6. 启动dfs: `start-dfs.sh`

现在所有的服务就已经启动了，我们可以观察两个节点上面的进程：`jps && ssh hd01-2 jps`，可以看到DN和NN在两个节点上面同时运行。

### 测试高可用

此时运行`hdfs dfs -tail /test/README.txt`将得到一个错误。因为默认情况，启动两个NN，两个的初始状态都是Standby，还没有Active NN。

运行`hdfs haadmin failover nn2 nn1`可将nn1设置为active，之后再运行上述命令即可成功。

1. 结束nn2上面的namenode，然后再尝试`hdfs dfs -tail /test/README.txt`，能看到warning，但是命令可以成功执行
2. 结束nn1上面的namenode，整个集群将无法使用，此时`hdfs haadmin failover nn1 nn2`成功，`hdfs dfs -tail /test/README.txt`又可以成功运行了

## NameNode手动高可用(JournalNodes)

如果想改为基于JournalNodes的高可用，当前还没有官方的方法。需要重头来一遍。

1. 先停止现有的服务：`stop-dfs.sh`

2. 删除已有的数据：`rm -rf data/hd01-1/data/hdfs/ && rm -rf data/hd01-2/data/hdfs/`

3. 修改配置`hdfs-site.xml`，将配置项`dfs.namenode.shared.edits.dir`替换为：

```xml
    <property>
        <name>dfs.namenode.shared.edits.dir</name>
        <value>qjournal://hd01-1:8485/mycluster</value>
    </property>
    <property>
        <name>dfs.journalnode.edits.dir</name>
        <value>/hd/data/hdfs/journal</value>
    </property>
```

修改`hadoop-env.sh`，加入配置：

```bash
export HDFS_JOURNALNODE_USER=root
```

4. 格式化namenode及journalnode，并初始化NN2:

```bash
hdfs --daemon start journalnode
hdfs namenode -format
start-dfs.sh
ssh hd01-2 bash -c "cd /app && source /app/env && hdfs namenode -bootstrapStandby"
ssh hd01-2 bash -c "cd /app && source /app/env && hdfs --daemon start namenode"
```

### 测试高可用

此时运行`hdfs dfs -mkdir /test && hdfs dfs -put hadoop/README.txt /test/`将得到一个错误。因为默认情况，启动两个NN，两个的初始状态都是Standby，还没有Active NN。

运行`hdfs haadmin failover nn2 nn1`可将nn1设置为active，之后再运行上述命令即可成功。

1. 结束nn2上面的namenode，然后再尝试`hdfs dfs -tail /test/README.txt`，能看到warning，但是命令可以成功执行
2. 结束nn1上面的namenode，整个集群将无法使用，此时`hdfs haadmin failover nn1 nn2`成功，`hdfs dfs -tail /test/README.txt`又可以成功运行了

## NameNode自动高可用

1. 先停止服务: `stop-dfs.sh`

2. 安装并启动一个zookeeper分布式一致性数据服务（这里为了简单，我们采用单节点zk）

```bash
cd /app
wget https://apache.website-solution.net/zookeeper/zookeeper-3.6.1/apache-zookeeper-3.6.1-bin.tar.gz
tar xf apache-zookeeper-3.6.1-bin.tar.gz
ln -sv apache-zookeeper-3.6.1-bin zookeeper

mkdir /app/data/zk && ln -sv /app/data/zk /hd/zk
cat > zookeeper/conf/zoo.cfg <<EOF
tickTime=2000
dataDir=/hd/zk/
clientPort=2181
EOF

cat >> env <<EOF
export ZK_HOME=/app/zookeeper
export PATH=\${ZK_HOME}/bin:\${PATH}
EOF
source ./env

zkServer.sh start

```

启动zk之后，我们可以通过`jps`看到一个新的进程：`QuorumPeerMain`

运行`zkCli.sh`，可以连接到zk，再执行`ls /`可以看到zk里面只有一个`zookeeper`节点。

3. 配置hadoop

修改`core-site.xml`，加入配置：

```xml
<property>
    <name>ha.zookeeper.quorum</name>
    <value>hd01-1:2181</value>
</property>
```

修改`hdfs-site.xml`，加入配置：

```xml
<property>
    <name>dfs.ha.automatic-failover.enabled</name>
    <value>true</value>
</property>
```

修改`hadoop-env.sh`，加入配置：

```bash
export HDFS_ZKFC_USER=root
```

4. 初始化：`hdfs zkfc -formatZK`。之后通过`zkCli.sh`查看节点，应该能看到`hadoop-ha`节点

5. 启动自动failover的集群：`start-dfs.sh`。此时用`jps`将能看到以下几个进程：

```
[root@hd01-1 app]# jps
2840 Jps
2538 DFSZKFailoverController   ---- 多出来的failover控制器进程
2027 NameNode
2188 DataNode
31405 QuorumPeerMain
```

6. 用`hdfs haadmin -getAllServiceState`查看NN的状态，可以观察到某一个NN为active

7. kill掉active的NN，用`hdfs haadmin -getAllServiceState`观察节点恢复情况，可以看到另一个节点变为`active`。运行`hdfs dfs -tail /test/README.txt`也能正常输出结果。


