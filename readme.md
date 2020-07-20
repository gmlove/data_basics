# Python基础知识训练

## IO流

使用StringIO或BytesIO可以把任意一个字符串或字节串当做文件流来使用。

多数时候，为了进行测试，我们不希望产生难以清理的临时文件。比如，当我们希望下载一张图片，并检查是否正确的下载了该图片的时候。

请编写`python`代码以实现：

1. 用[`requests`](https://requests.readthedocs.io/zh_CN/latest/)库下载图片`https://www.baidu.com/img/PCtm_d9c8750bed0b3c7d089fa7d55720d6cf.png`
2. 用[`PIL`](https://pillow.readthedocs.io/en/stable/reference/Image.html)库以流的方式读取此图片的内容
3. 用[`matplotlib`](https://matplotlib.org/3.2.2/api/_as_gen/matplotlib.pyplot.imshow.html)中的`matplotlib.pyplot.imshow`函数显示该图片
