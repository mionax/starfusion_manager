// Authing 配置文件
const AuthingConfig = {
  // Authing 应用配置
  appId: '682f21a28c586cf53b6d7dc1', // 应用ID，需要替换为您在Authing控制台获取的应用ID
  appHost: 'https://starfusion.authing.cn', // 应用域名
  redirectUri: window.location.origin + '/web/authing_callback.html', // 登录回调地址
  
  // Guard 配置
  guardOptions: {
    appId: '682f21a28c586cf53b6d7dc1', // 应用ID
    mode: 'normal', // 模式：normal | modal
    defaultScene: 'login', // 默认场景：login | register
    logo: null, // 显示在登录框上方的Logo
    title: '星汇工作流', // 登录框标题
    autoRegister: true, // 是否开启自动注册
    loginMethods: ['password', 'phone-code'], // 可用的登录方式
    defaultLoginMethod: 'password', // 默认登录方式
    socialConnections: ['github'], // 社交登录方式
    
    // 额外配置，提高稳定性
    host: {
      user: 'https://starfusion.authing.cn',
      oauth: 'https://starfusion.authing.cn'
    },
    
    // 回调处理
    redirectUri: window.location.origin + '/web/authing_callback.html',
    
    // 语言和定制化
    lang: 'zh-CN', // 语言
    contentCss: '.g2-view-header { background: linear-gradient(90deg, #3a4a6a 0%, #2a8cff 100%); }' // 自定义CSS
  },
  
  // 其他配置
  tokenLocalStorageKey: 'userToken', // 存储token的localStorage键名
  userInfoLocalStorageKey: 'userInfo', // 存储用户信息的localStorage键名
};

// 导出配置
export default AuthingConfig; 