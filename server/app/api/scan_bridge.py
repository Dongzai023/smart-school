"""
微信扫码桥接页面

教师用微信扫描希沃一体机锁屏上的二维码时，
微信会用内置浏览器打开 https://lock.qjzxmd.cn/scan-unlock?device_id=xxx
此路由返回一个 HTML 页面，通过微信 JSSDK 自动跳转到小程序的解锁页面。
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["扫码桥接"])


@router.get("/scan-unlock", response_class=HTMLResponse)
def scan_unlock_bridge(device_id: str = ""):
    """扫码桥接页面：引导用户跳转到微信小程序解锁页面。"""
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>扫码解锁 - 清涧中学</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
            text-align: center;
            padding: 30px;
        }}
        .icon {{ font-size: 64px; margin-bottom: 20px; }}
        h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 12px; }}
        p {{ font-size: 15px; color: #aaa; line-height: 1.6; margin-bottom: 30px; }}
        .btn {{
            background: linear-gradient(135deg, #07c160, #059a49);
            color: white;
            border: none;
            border-radius: 50px;
            padding: 14px 36px;
            font-size: 17px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            box-shadow: 0 4px 20px rgba(7, 193, 96, 0.4);
        }}
        .hint {{ font-size: 13px; color: #666; margin-top: 20px; }}
        #auto-msg {{ color: #07c160; font-size: 14px; margin-top: 15px; }}
    </style>
</head>
<body>
    <div class="icon">🔐</div>
    <h1>希沃一体机解锁</h1>
    <p>正在跳转至签到小程序进行身份验证...<br>请稍候或点击下方按钮手动打开。</p>
    <wx-open-launch-miniprogram
        id="launch-btn"
        username="gh_xxxxxxxx"
        path="pages/scan-unlock/scan-unlock?device_id={device_id}"
        style="display: none;"
    >
        <script type="text/wxtag-template">
            <style>.btn{{ display: inline-block; padding: 14px 36px; background: #07c160; color: white; border-radius: 50px; font-size: 17px; }}</style>
            <div class="btn">打开小程序解锁</div>
        </script>
    </wx-open-launch-miniprogram>
    <a class="btn" href="/scan-unlock?device_id={device_id}" id="fallback-btn" style="display:none;">在小程序中解锁</a>
    <p class="hint">如无法自动跳转，请长按本页面 → 「选择小程序」打开</p>
    <div id="auto-msg"></div>

    <script src="https://res.wx.qq.com/open/js/jweixin-1.6.0.js"></script>
    <script>
        const deviceId = '{device_id}';
        const ua = navigator.userAgent.toLowerCase();
        const isWeChat = ua.indexOf('micromessenger') !== -1;
        const autoMsg = document.getElementById('auto-msg');

        if (isWeChat) {{
            // 在微信中：使用 JSSDK 跳转小程序
            wx.miniProgram.getEnv(function(res) {{
                if (res.miniprogram) {{
                    // Already inside mini program
                    autoMsg.textContent = '已在小程序中，请刷新页面。';
                }} else {{
                    // In WeChat browser - navigate to mini program
                    wx.miniProgram.navigateTo({{
                        url: '/pages/scan-unlock/scan-unlock?device_id=' + deviceId,
                        success: function() {{
                            autoMsg.textContent = '跳转中...';
                        }},
                        fail: function() {{
                            autoMsg.textContent = '自动跳转失败，请长按页面选择打开小程序。';
                        }}
                    }});
                }}
            }});
        }} else {{
            autoMsg.textContent = '请用微信扫描二维码打开此页面。';
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)
