# 改版 （小爱音箱 Pro）

旧版本用不了了，临时换个新方法

在此网站[https://debugger.iot.mi.com/iot/devices](https://debugger.iot.mi.com/iot/devices)获取需要的参数

从请求 `headers` 中获取，`APP-ID`, `ACCESS-TOKEN`
从页面中获取 `设备ID`

配置例子,填写绑定小爱音箱的用户账号信息：

```yaml
hello_miai:
  appid: 'APP-ID'
  token: 'ACCESS-TOKEN'
  deviceid: 'xxxxxx'

  # 可选全局配置 - 此处为协议中对应的 iid 值
  params:
    force_send: "5.1"
    add2msgqueue: "5.1"
    set_vol: "2.1"
    execution: "5.5"

```

调用服务

```yaml
wait_time: 0
message: 你好，我不是小爱。
```
