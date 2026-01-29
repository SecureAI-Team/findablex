# SSL 证书目录

将阿里云 SSL 证书文件放到此目录:

```
ssl/
├── findablex.com.pem     # 证书文件 (包含中间证书)
├── findablex.com.key     # 私钥文件
└── README.md
```

## 证书命名

从阿里云下载 Nginx 格式证书后，重命名为：
- `findablex.com.pem` - 证书文件
- `findablex.com.key` - 私钥文件

## 部署步骤

1. 将证书文件上传到此目录
2. 运行部署脚本: `sudo bash deploy.sh start`

## 证书路径

在 nginx.conf 中配置为：
```nginx
ssl_certificate /etc/nginx/ssl/findablex.com.pem;
ssl_certificate_key /etc/nginx/ssl/findablex.com.key;
```
