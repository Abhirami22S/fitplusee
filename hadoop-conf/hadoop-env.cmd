@rem FitPulse Hadoop environment (sourced by hadoop/hdfs .cmd launchers via HADOOP_CONF_DIR)
set JAVA_HOME=D:\bigdata\fitpulsee\tools\jdk17
set HADOOP_HEAPSIZE_MAX=512m
@rem JDK 17 strong encapsulation: Hadoop 3.4.x needs these opens
set HADOOP_OPTS=%HADOOP_OPTS% --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED --add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/java.io=ALL-UNNAMED --add-opens=java.base/java.net=ALL-UNNAMED --add-opens=java.base/java.util.concurrent=ALL-UNNAMED --add-opens=java.base/java.lang.reflect=ALL-UNNAMED --add-opens=java.base/java.text=ALL-UNNAMED
