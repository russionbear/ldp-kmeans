
目录结构
    /README.md                  git相关
    /.gitignore                 git相关

    /cache                      缓存文件路径
    /localstorageKeams          数据集路径
        - */from.scv                原始数据
        - */to.csv                  处理后的聚类结果
        - */state.txt               保存数据集的信息，内容为json格式
        - */rlt.png                 处理后的二维数据图片
        - /log                      保存程序的错误信息
        - /user                     用户信息 内容为json格式
    /source                     存放图片资源
        - /icon.*                   界面图标
        - /images.py                里面的每个变量的值为字符串，字符串是由二进制图片数据经base64处理后得来的
    /test_dataset               保存用来测试的数据集

    /tools
        - /builder.py               用来将二进制图片数据转为字符串并写入到 /source/images.py
        - /make_data.py             制作算法程序的测试数据
    /encipher.py                对用户的密码进行加密、解密
    /LDP_Searching.m            由matlab打包的可被python调用的文件
    /myCpu.py                   内有数据预处理和基于ldp-kmeans离群检测算法的程序
    /login.py                   界面程序，程序的入口文件