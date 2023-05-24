#!/bin/bash

# 定义文件路径和名称
tar_file=$(pwd)/osr_otg.tar.gz
target_dir=/data/ai/

# 检查tar包是否存在
if [ ! -f $tar_file ]; then
    echo " osr_otg update otg package is not exist!"
    exit 1
fi

# 检查目标目录是否存在,不存在则创建
if [ ! -d $target_dir ]; then
    mkdir -p $target_dir
fi

# 切换到目标目录
cd $target_dir

# 解压tar包
tar -zxvf $tar_file

echo "Unzip successfully! restart ocr_speech_rec container..."

# 定义容器名称
container_name=ocr_speech_rec

# 检查容器是否存在
container_id=$(docker ps -a | grep $container_name | awk '{print $1}')

if [ -n "$container_id" ]; then
    # 容器存在,停止并移除旧容器
    docker restart $container_name
else
    # 容器不存在,运行新容器
    docker run -it -d --restart=unless-stopped --cpus=4 --network=host -v /data/ai:/data/ai --name $container_name registry.cn-beijing.aliyuncs.com/minok/ocr_speech_rec /bin/bash
fi
echo "Update successfully！"