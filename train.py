from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import datetime
import time
import os  # 引入 os 模組以讀取環境變數
app = Flask(__name__)
# 設置 Gmail SMTP 參數
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def get_token(session, url, token_name):
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    token = soup.find('input', {'name': token_name})
    return token['value'] if token else None

def query_train_request(startStation, endStation, rideDate, startTime, endTime, pid):
    session = requests.Session()
    query_url = 'https://www.railway.gov.tw/tra-tip-web/tip/tip001/tip123/query'
    post_url = 'https://www.railway.gov.tw/tra-tip-web/tip/tip001/tip123/queryTrain'
    
    csrf_token = get_token(session, query_url, '_csrf')
    complete_token = get_token(session, query_url, 'completeToken')
    if not csrf_token:
        return {"error": "無法取得 CSRF Token"}
    if not complete_token:
        complete_token = "nug+6Z1wgkpk9Koiv2SwmA=="
    
    data = [
        ("_csrf", csrf_token),
        ("custIdTypeEnum", "PERSON_ID"),
        ("pid", pid),
        ("tripType", "ONEWAY"),
        ("orderType", "BY_TIME"),
        ("ticketOrderParamList[0].tripNo", "TRIP1"),
        ("ticketOrderParamList[0].startStation", startStation),
        ("ticketOrderParamList[0].endStation", endStation),
        ("ticketOrderParamList[0].rideDate", rideDate),
        ("ticketOrderParamList[0].startOrEndTime", "true"),
        ("ticketOrderParamList[0].startTime", startTime),
        ("ticketOrderParamList[0].endTime", endTime),
        ("ticketOrderParamList[0].normalQty", "1"),
        ("ticketOrderParamList[0].wheelChairQty", "0"),
        ("ticketOrderParamList[0].parentChildQty", "0"),
        ("ticketOrderParamList[0].trainTypeList", "11"),
        ("_ticketOrderParamList[0].trainTypeList", "on"),
        ("ticketOrderParamList[0].trainTypeList", "1"),
        ("_ticketOrderParamList[0].trainTypeList", "on"),
        ("ticketOrderParamList[0].trainTypeList", "2"),
        ("_ticketOrderParamList[0].trainTypeList", "on"),
        ("ticketOrderParamList[0].trainTypeList", "3"),
        ("_ticketOrderParamList[0].trainTypeList", "on"),
        ("ticketOrderParamList[0].trainTypeList", "4"),
        ("_ticketOrderParamList[0].trainTypeList", "on"),
        ("ticketOrderParamList[0].trainTypeList", "5"),
        ("_ticketOrderParamList[0].trainTypeList", "on"),
        ("ticketOrderParamList[0].chgSeat", "true"),
        ("_ticketOrderParamList[0].chgSeat", "on"),
        ("ticketOrderParamList[0].seatPref", "NONE"),
        ("completeToken", complete_token)
    ]
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": query_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        response = session.post(post_url, data=data, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"請求失敗: {str(e)}"}
    
    soup = BeautifulSoup(response.text, "html.parser")
    trip_rows = soup.find_all("tr", class_="trip-column")
    results = []
    if trip_rows:
        for row in trip_rows:
            train_ul = row.find("ul", class_="train-number")
            if train_ul:
                a_tag = train_ul.find("a")
                train_info = a_tag.get_text(strip=True) if a_tag else "未知車次"
                ride_date = a_tag.get('href', '').split('rideDate=')[1].split('&')[0] if a_tag and 'rideDate=' in a_tag.get('href', '') else rideDate
                ride_date_short = ride_date[5:]
            else:
                train_info = "未知車次"
                ride_date_short = rideDate[5:]
            
            tds = row.find_all("td")
            if len(tds) >= 4:
                departure_time = tds[2].get_text(strip=True)
                arrival_time = tds[3].get_text(strip=True)
                time_info = f"{ride_date_short} {departure_time}-{arrival_time}"
            else:
                time_info = f"{ride_date_short} 未知時間"
            results.append({"train": train_info, "time": time_info})
        return {"found": True, "results": results}
    else:
        warning = soup.find("h2", class_="icon-fa warning")
        if warning:
            return {"found": False, "message": "您所查詢的條件，均沒有空位。"}
        else:
            return {"found": False, "message": "未找到明確的查詢結果。"}

def send_email(recipient, subject, body, smtp_username, smtp_app_password):
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = smtp_username
        msg['To'] = recipient

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(smtp_username, smtp_app_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"寄送 Email 失敗: {str(e)}")
        return False

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>台鐵查詢系統</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <style>
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 16px;
            height: 16px;
            animation: spin 1s linear infinite;
            display: inline-block;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .flatpickr-input {
            width: 200px;
            padding: 5px;
        }
        select {
            width: 220px;
            padding: 5px;
        }
        .station-search {
            width: 200px;
            padding: 5px;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    <h1>台鐵查詢系統</h1>
    <h1>輸入請參考 https://www.railway.gov.tw/tra-tip-web/tip/tip001/tip123/query</h1>
    <form id="queryForm">
        <label>起始車站：</label><br>
        <input type="text" id="startStationSearch" class="station-search" placeholder="輸入站名或代碼搜尋"><br>
        <select id="startStation" name="startStation">
            <option value="">請選擇起始車站</option>
            <optgroup label="西部幹線">
                <option value="0900-基隆">基隆 (0900)</option>
                <option value="0910-三坑">三坑 (0910)</option>
                <option value="0920-八堵">八堵 (0920)</option>
                <option value="0930-七堵">七堵 (0930)</option>
                <option value="0940-百福">百福 (0940)</option>
                <option value="0950-五堵">五堵 (0950)</option>
                <option value="0960-汐止">汐止 (0960)</option>
                <option value="0970-汐科">汐科 (0970)</option>
                <option value="0980-南港">南港 (0980)</option>
                <option value="0990-松山">松山 (0990)</option>
                <option value="1000-臺北" selected>臺北 (1000)</option>
                <option value="1010-萬華">萬華 (1010)</option>
                <option value="1020-板橋">板橋 (1020)</option>
                <option value="1030-浮洲">浮洲 (1030)</option>
                <option value="1040-樹林">樹林 (1040)</option>
                <option value="1050-南樹林">南樹林 (1050)</option>
                <option value="1060-山佳">山佳 (1060)</option>
                <option value="1070-鶯歌">鶯歌 (1070)</option>
                <option value="1080-桃園">桃園 (1080)</option>
                <option value="1090-內壢">內壢 (1090)</option>
                <option value="1100-中壢">中壢 (1100)</option>
                <option value="1110-埔心">埔心 (1110)</option>
                <option value="1120-楊梅">楊梅 (1120)</option>
                <option value="1130-富岡">富岡 (1130)</option>
                <option value="1140-新富">新富 (1140)</option>
                <option value="1150-北湖">北湖 (1150)</option>
                <option value="1160-湖口">湖口 (1160)</option>
                <option value="1170-新豐">新豐 (1170)</option>
                <option value="1180-竹北">竹北 (1180)</option>
                <option value="1190-北新竹">北新竹 (1190)</option>
                <option value="1210-新竹">新竹 (1210)</option>
                <option value="1220-三姓橋">三姓橋 (1220)</option>
                <option value="1230-香山">香山 (1230)</option>
                <option value="1240-崎頂">崎頂 (1240)</option>
                <option value="1250-竹南">竹南 (1250)</option>
                <option value="3140-造橋">造橋 (3140)</option>
                <option value="3150-豐富">豐富 (3150)</option>
                <option value="3160-苗栗">苗栗 (3160)</option>
                <option value="3170-南勢">南勢 (3170)</option>
                <option value="3180-銅鑼">銅鑼 (3180)</option>
                <option value="3190-三義">三義 (3190)</option>
                <option value="3210-泰安">泰安 (3210)</option>
                <option value="3220-后里">后里 (3220)</option>
                <option value="3230-豐原">豐原 (3230)</option>
                <option value="3240-栗林">栗林 (3240)</option>
                <option value="3250-潭子">潭子 (3250)</option>
                <option value="3260-頭家厝">頭家厝 (3260)</option>
                <option value="3270-松竹">松竹 (3270)</option>
                <option value="3280-太原">太原 (3280)</option>
                <option value="3290-精武">精武 (3290)</option>
                <option value="3300-臺中">臺中 (3300)</option>
                <option value="3310-五權">五權 (3310)</option>
                <option value="3320-大慶">大慶 (3320)</option>
                <option value="3330-烏日">烏日 (3330)</option>
                <option value="3340-新烏日">新烏日 (3340)</option>
                <option value="3350-成功">成功 (3350)</option>
                <option value="3360-彰化">彰化 (3360)</option>
                <option value="3370-花壇">花壇 (3370)</option>
                <option value="3380-大村">大村 (3380)</option>
                <option value="3390-員林">員林 (3390)</option>
                <option value="3400-永靖">永靖 (3400)</option>
                <option value="3410-社頭">社頭 (3410)</option>
                <option value="3420-田中">田中 (3420)</option>
                <option value="3430-二水">二水 (3430)</option>
                <option value="3450-林內">林內 (3450)</option>
                <option value="3460-石榴">石榴 (3460)</option>
                <option value="3470-斗六">斗六 (3470)</option>
                <option value="3480-斗南">斗南 (3480)</option>
                <option value="3490-石龜">石龜 (3490)</option>
                <option value="4050-大林">大林 (4050)</option>
                <option value="4060-民雄">民雄 (4060)</option>
                <option value="4070-嘉北">嘉北 (4070)</option>
                <option value="4080-嘉義">嘉義 (4080)</option>
                <option value="4090-水上">水上 (4090)</option>
                <option value="4100-南靖">南靖 (4100)</option>
                <option value="4110-後壁">後壁 (4110)</option>
                <option value="4120-新營">新營 (4120)</option>
                <option value="4130-柳營">柳營 (4130)</option>
                <option value="4140-林鳳營">林鳳營 (4140)</option>
                <option value="4150-隆田">隆田 (4150)</option>
                <option value="4160-拔林">拔林 (4160)</option>
                <option value="4170-善化">善化 (4170)</option>
                <option value="4180-南科">南科 (4180)</option>
                <option value="4190-新市">新市 (4190)</option>
                <option value="4200-永康">永康 (4200)</option>
                <option value="4210-大橋">大橋 (4210)</option>
                <option value="4220-臺南">臺南 (4220)</option>
                <option value="4230-林森">林森 (4230)</option>
                <option value="4240-南臺南">南臺南 (4240)</option>
                <option value="4250-保安">保安 (4250)</option>
                <option value="4260-仁德">仁德 (4260)</option>
                <option value="4270-中洲">中洲 (4270)</option>
                <option value="4290-大湖">大湖 (4290)</option>
                <option value="4300-路竹">路竹 (4300)</option>
                <option value="4310-岡山">岡山 (4310)</option>
                <option value="4320-橋頭">橋頭 (4320)</option>
                <option value="4330-楠梓">楠梓 (4330)</option>
                <option value="4340-新左營">新左營 (4340)</option>
                <option value="4350-左營">左營 (4350)</option>
                <option value="4360-內惟">內惟 (4360)</option>
                <option value="4370-美術館">美術館 (4370)</option>
                <option value="4380-鼓山">鼓山 (4380)</option>
                <option value="4390-三塊厝">三塊厝 (4390)</option>
                <option value="4400-高雄">高雄 (4400)</option>
                <option value="4410-民族">民族 (4410)</option>
                <option value="4420-科工館">科工館 (4420)</option>
                <option value="4430-正義">正義 (4430)</option>
                <option value="4440-鳳山">鳳山 (4440)</option>
                <option value="4450-後庄">後庄 (4450)</option>
                <option value="4460-九曲堂">九曲堂 (4460)</option>
                <option value="4470-六塊厝">六塊厝 (4470)</option>
                <option value="5000-屏東">屏東 (5000)</option>
            </optgroup>
            <optgroup label="西部幹線-海線">
                <option value="2110-談文">談文 (2110)</option>
                <option value="2120-大山">大山 (2120)</option>
                <option value="2130-後龍">後龍 (2130)</option>
                <option value="2140-龍港">龍港 (2140)</option>
                <option value="2150-白沙屯">白沙屯 (2150)</option>
                <option value="2160-新埔">新埔 (2160)</option>
                <option value="2170-通霄">通霄 (2170)</option>
                <option value="2180-苑裡">苑裡 (2180)</option>
                <option value="2190-日南">日南 (2190)</option>
                <option value="2200-大甲">大甲 (2200)</option>
                <option value="2210-臺中港">臺中港 (2210)</option>
                <option value="2220-清水">清水 (2220)</option>
                <option value="2230-沙鹿">沙鹿 (2230)</option>
                <option value="2240-龍井">龍井 (2240)</option>
                <option value="2250-大肚">大肚 (2250)</option>
                <option value="2260-追分">追分 (2260)</option>
            </optgroup>
            <optgroup label="東部幹線">
                <option value="0920-八堵">八堵 (0920)</option>
                <option value="7390-暖暖">暖暖 (7390)</option>
                <option value="7380-四腳亭">四腳亭 (7380)</option>
                <option value="7360-瑞芳">瑞芳 (7360)</option>
                <option value="7350-猴硐">猴硐 (7350)</option>
                <option value="7330-三貂嶺">三貂嶺 (7330)</option>
                <option value="7320-牡丹">牡丹 (7320)</option>
                <option value="7310-雙溪">雙溪 (7310)</option>
                <option value="7300-貢寮">貢寮 (7300)</option>
                <option value="7290-福隆">福隆 (7290)</option>
                <option value="7280-石城">石城 (7280)</option>
                <option value="7270-大里">大里 (7270)</option>
                <option value="7260-大溪">大溪 (7260)</option>
                <option value="7250-龜山">龜山 (7250)</option>
                <option value="7240-外澳">外澳 (7240)</option>
                <option value="7230-頭城">頭城 (7230)</option>
                <option value="7220-頂埔">頂埔 (7220)</option>
                <option value="7210-礁溪">礁溪 (7210)</option>
                <option value="7200-四城">四城 (7200)</option>
                <option value="7190-宜蘭">宜蘭 (7190)</option>
                <option value="7180-二結">二結 (7180)</option>
                <option value="7170-中里">中里 (7170)</option>
                <option value="7160-羅東">羅東 (7160)</option>
                <option value="7150-冬山">冬山 (7150)</option>
                <option value="7140-新馬">新馬 (7140)</option>
                <option value="7130-蘇澳新站">蘇澳新站 (7130)</option>
                <option value="7120-蘇澳">蘇澳 (7120)</option>
                <option value="7110-永樂">永樂 (7110)</option>
                <option value="7100-東澳">東澳 (7100)</option>
                <option value="7090-南澳">南澳 (7090)</option>
                <option value="7080-武塔">武塔 (7080)</option>
                <option value="7070-漢本">漢本 (7070)</option>
                <option value="7060-和平">和平 (7060)</option>
                <option value="7050-和仁">和仁 (7050)</option>
                <option value="7040-崇德">崇德 (7040)</option>
                <option value="7030-新城">新城 (7030)</option>
                <option value="7020-景美">景美 (7020)</option>
                <option value="7010-北埔">北埔 (7010)</option>
                <option value="7000-花蓮">花蓮 (7000)</option>
                <option value="6250-吉安">吉安 (6250)</option>
                <option value="6240-志學">志學 (6240)</option>
                <option value="6230-平和">平和 (6230)</option>
                <option value="6220-壽豐">壽豐 (6220)</option>
                <option value="6210-豐田">豐田 (6210)</option>
                <option value="6200-林榮新光">林榮新光 (6200)</option>
                <option value="6190-南平">南平 (6190)</option>
                <option value="6180-鳳林">鳳林 (6180)</option>
                <option value="6170-萬榮">萬榮 (6170)</option>
                <option value="6160-光復">光復 (6160)</option>
                <option value="6150-大富">大富 (6150)</option>
                <option value="6140-富源">富源 (6140)</option>
                <option value="6130-瑞穗">瑞穗 (6130)</option>
                <option value="6120-三民">三民 (6120)</option>
                <option value="6110-玉里">玉里 (6110)</option>
                <option value="6100-東里">東里 (6100)</option>
                <option value="6090-東竹">東竹 (6090)</option>
                <option value="6080-富里">富里 (6080)</option>
                <option value="6070-池上">池上 (6070)</option>
                <option value="6060-海端">海端 (6060)</option>
                <option value="6050-關山">關山 (6050)</option>
                <option value="6040-瑞和">瑞和 (6040)</option>
                <option value="6030-瑞源">瑞源 (6030)</option>
                <option value="6020-鹿野">鹿野 (6020)</option>
                <option value="6010-山里">山里 (6010)</option>
                <option value="6000-臺東">臺東 (6000)</option>
            </optgroup>
            <optgroup label="屏東-南迴線">
                <option value="5000-屏東">屏東 (5000)</option>
                <option value="5010-歸來">歸來 (5010)</option>
                <option value="5020-麟洛">麟洛 (5020)</option>
                <option value="5030-西勢">西勢 (5030)</option>
                <option value="5040-竹田">竹田 (5040)</option>
                <option value="5050-潮州">潮州 (5050)</option>
                <option value="5060-崁頂">崁頂 (5060)</option>
                <option value="5070-南州">南州 (5070)</option>
                <option value="5080-鎮安">鎮安 (5080)</option>
                <option value="5090-林邊">林邊 (5090)</option>
                <option value="5100-佳冬">佳冬 (5100)</option>
                <option value="5110-東海">東海 (5110)</option>
                <option value="5120-枋寮">枋寮 (5120)</option>
                <option value="5130-加祿">加祿 (5130)</option>
                <option value="5140-內獅">內獅 (5140)</option>
                <option value="5160-枋山">枋山 (5160)</option>
                <option value="5190-大武">大武 (5190)</option>
                <option value="5200-瀧溪">瀧溪 (5200)</option>
                <option value="5210-金崙">金崙 (5210)</option>
                <option value="5220-太麻里">太麻里 (5220)</option>
                <option value="5230-知本">知本 (5230)</option>
                <option value="5240-康樂">康樂 (5240)</option>
                <option value="6000-臺東">臺東 (6000)</option>
            </optgroup>
            <optgroup label="平溪線">
                <option value="7330-三貂嶺">三貂嶺 (7330)</option>
                <option value="7331-大華">大華 (7331)</option>
                <option value="7332-十分">十分 (7332)</option>
                <option value="7333-望古">望古 (7333)</option>
                <option value="7334-嶺腳">嶺腳 (7334)</option>
                <option value="7335-平溪">平溪 (7335)</option>
                <option value="7336-菁桐">菁桐 (7336)</option>
            </optgroup>
            <optgroup label="內灣線">
                <option value="1210-新竹">新竹 (1210)</option>
                <option value="1190-北新竹">北新竹 (1190)</option>
                <option value="1191-千甲">千甲 (1191)</option>
                <option value="1192-新莊">新莊 (1192)</option>
                <option value="1193-竹中">竹中 (1193)</option>
                <option value="1201-上員">上員 (1201)</option>
                <option value="1202-榮華">榮華 (1202)</option>
                <option value="1203-竹東">竹東 (1203)</option>
                <option value="1204-橫山">橫山 (1204)</option>
                <option value="1205-九讚頭">九讚頭 (1205)</option>
                <option value="1206-合興">合興 (1206)</option>
                <option value="1207-富貴">富貴 (1207)</option>
                <option value="1208-內灣">內灣 (1208)</option>
            </optgroup>
            <optgroup label="集集線">
                <option value="3430-二水">二水 (3430)</option>
                <option value="3431-源泉">源泉 (3431)</option>
                <option value="3432-濁水">濁水 (3432)</option>
                <option value="3433-龍泉">龍泉 (3433)</option>
                <option value="3434-集集">集集 (3434)</option>
                <option value="3435-水里">水里 (3435)</option>
                <option value="3436-車埕">車埕 (3436)</option>
            </optgroup>
            <optgroup label="成追線">
                <option value="3350-成功">成功 (3350)</option>
                <option value="2260-追分">追分 (2260)</option>
            </optgroup>
            <optgroup label="沙崙線">
                <option value="4270-中洲">中洲 (4270)</option>
                <option value="4271-長榮大學">長榮大學 (4271)</option>
                <option value="4272-沙崙">沙崙 (4272)</option>
            </optgroup>
            <optgroup label="六家線">
                <option value="1193-竹中">竹中 (1193)</option>
                <option value="1194-六家">六家 (1194)</option>
            </optgroup>
            <optgroup label="深澳線">
                <option value="7360-瑞芳">瑞芳 (7360)</option>
                <option value="7361-海科館">海科館 (7361)</option>
                <option value="7362-八斗子">八斗子 (7362)</option>
            </optgroup>
        </select><br>
        <label>抵達站：</label><br>
        <input type="text" id="endStationSearch" class="station-search" placeholder="輸入站名或代碼搜尋"><br>
        <select id="endStation" name="endStation">
            <option value="">請選擇抵達車站</option>
            <optgroup label="西部幹線">
                <option value="0900-基隆">基隆 (0900)</option>
                <option value="0910-三坑">三坑 (0910)</option>
                <option value="0920-八堵">八堵 (0920)</option>
                <option value="0930-七堵">七堵 (0930)</option>
                <option value="0940-百福">百福 (0940)</option>
                <option value="0950-五堵">五堵 (0950)</option>
                <option value="0960-汐止">汐止 (0960)</option>
                <option value="0970-汐科">汐科 (0970)</option>
                <option value="0980-南港">南港 (0980)</option>
                <option value="0990-松山">松山 (0990)</option>
                <option value="1000-臺北">臺北 (1000)</option>
                <option value="1010-萬華">萬華 (1010)</option>
                <option value="1020-板橋">板橋 (1020)</option>
                <option value="1030-浮洲">浮洲 (1030)</option>
                <option value="1040-樹林">樹林 (1040)</option>
                <option value="1050-南樹林">南樹林 (1050)</option>
                <option value="1060-山佳">山佳 (1060)</option>
                <option value="1070-鶯歌">鶯歌 (1070)</option>
                <option value="1080-桃園">桃園 (1080)</option>
                <option value="1090-內壢">內壢 (1090)</option>
                <option value="1100-中壢">中壢 (1100)</option>
                <option value="1110-埔心">埔心 (1110)</option>
                <option value="1120-楊梅">楊梅 (1120)</option>
                <option value="1130-富岡">富岡 (1130)</option>
                <option value="1140-新富">新富 (1140)</option>
                <option value="1150-北湖">北湖 (1150)</option>
                <option value="1160-湖口">湖口 (1160)</option>
                <option value="1170-新豐">新豐 (1170)</option>
                <option value="1180-竹北">竹北 (1180)</option>
                <option value="1190-北新竹">北新竹 (1190)</option>
                <option value="1210-新竹">新竹 (1210)</option>
                <option value="1220-三姓橋">三姓橋 (1220)</option>
                <option value="1230-香山">香山 (1230)</option>
                <option value="1240-崎頂">崎頂 (1240)</option>
                <option value="1250-竹南">竹南 (1250)</option>
                <option value="3140-造橋">造橋 (3140)</option>
                <option value="3150-豐富">豐富 (3150)</option>
                <option value="3160-苗栗">苗栗 (3160)</option>
                <option value="3170-南勢">南勢 (3170)</option>
                <option value="3180-銅鑼">銅鑼 (3180)</option>
                <option value="3190-三義">三義 (3190)</option>
                <option value="3210-泰安">泰安 (3210)</option>
                <option value="3220-后里">后里 (3220)</option>
                <option value="3230-豐原">豐原 (3230)</option>
                <option value="3240-栗林">栗林 (3240)</option>
                <option value="3250-潭子">潭子 (3250)</option>
                <option value="3260-頭家厝">頭家厝 (3260)</option>
                <option value="3270-松竹">松竹 (3270)</option>
                <option value="3280-太原">太原 (3280)</option>
                <option value="3290-精武">精武 (3290)</option>
                <option value="3300-臺中" selected>臺中 (3300)</option>
                <option value="3310-五權">五權 (3310)</option>
                <option value="3320-大慶">大慶 (3320)</option>
                <option value="3330-烏日">烏日 (3330)</option>
                <option value="3340-新烏日">新烏日 (3340)</option>
                <option value="3350-成功">成功 (3350)</option>
                <option value="3360-彰化">彰化 (3360)</option>
                <option value="3370-花壇">花壇 (3370)</option>
                <option value="3380-大村">大村 (3380)</option>
                <option value="3390-員林">員林 (3390)</option>
                <option value="3400-永靖">永靖 (3400)</option>
                <option value="3410-社頭">社頭 (3410)</option>
                <option value="3420-田中">田中 (3420)</option>
                <option value="3430-二水">二水 (3430)</option>
                <option value="3450-林內">林內 (3450)</option>
                <option value="3460-石榴">石榴 (3460)</option>
                <option value="3470-斗六">斗六 (3470)</option>
                <option value="3480-斗南">斗南 (3480)</option>
                <option value="3490-石龜">石龜 (3490)</option>
                <option value="4050-大林">大林 (4050)</option>
                <option value="4060-民雄">民雄 (4060)</option>
                <option value="4070-嘉北">嘉北 (4070)</option>
                <option value="4080-嘉義">嘉義 (4080)</option>
                <option value="4090-水上">水上 (4090)</option>
                <option value="4100-南靖">南靖 (4100)</option>
                <option value="4110-後壁">後壁 (4110)</option>
                <option value="4120-新營">新營 (4120)</option>
                <option value="4130-柳營">柳營 (4130)</option>
                <option value="4140-林鳳營">林鳳營 (4140)</option>
                <option value="4150-隆田">隆田 (4150)</option>
                <option value="4160-拔林">拔林 (4160)</option>
                <option value="4170-善化">善化 (4170)</option>
                <option value="4180-南科">南科 (4180)</option>
                <option value="4190-新市">新市 (4190)</option>
                <option value="4200-永康">永康 (4200)</option>
                <option value="4210-大橋">大橋 (4210)</option>
                <option value="4220-臺南">臺南 (4220)</option>
                <option value="4230-林森">林森 (4230)</option>
                <option value="4240-南臺南">南臺南 (4240)</option>
                <option value="4250-保安">保安 (4250)</option>
                <option value="4260-仁德">仁德 (4260)</option>
                <option value="4270-中洲">中洲 (4270)</option>
                <option value="4290-大湖">大湖 (4290)</option>
                <option value="4300-路竹">路竹 (4300)</option>
                <option value="4310-岡山">岡山 (4310)</option>
                <option value="4320-橋頭">橋頭 (4320)</option>
                <option value="4330-楠梓">楠梓 (4330)</option>
                <option value="4340-新左營">新左營 (4340)</option>
                <option value="4350-左營">左營 (4350)</option>
                <option value="4360-內惟">內惟 (4360)</option>
                <option value="4370-美術館">美術館 (4370)</option>
                <option value="4380-鼓山">鼓山 (4380)</option>
                <option value="4390-三塊厝">三塊厝 (4390)</option>
                <option value="4400-高雄">高雄 (4400)</option>
                <option value="4410-民族">民族 (4410)</option>
                <option value="4420-科工館">科工館 (4420)</option>
                <option value="4430-正義">正義 (4430)</option>
                <option value="4440-鳳山">鳳山 (4440)</option>
                <option value="4450-後庄">後庄 (4450)</option>
                <option value="4460-九曲堂">九曲堂 (4460)</option>
                <option value="4470-六塊厝">六塊厝 (4470)</option>
                <option value="5000-屏東">屏東 (5000)</option>
            </optgroup>
            <optgroup label="西部幹線-海線">
                <option value="2110-談文">談文 (2110)</option>
                <option value="2120-大山">大山 (2120)</option>
                <option value="2130-後龍">後龍 (2130)</option>
                <option value="2140-龍港">龍港 (2140)</option>
                <option value="2150-白沙屯">白沙屯 (2150)</option>
                <option value="2160-新埔">新埔 (2160)</option>
                <option value="2170-通霄">通霄 (2170)</option>
                <option value="2180-苑裡">苑裡 (2180)</option>
                <option value="2190-日南">日南 (2190)</option>
                <option value="2200-大甲">大甲 (2200)</option>
                <option value="2210-臺中港">臺中港 (2210)</option>
                <option value="2220-清水">清水 (2220)</option>
                <option value="2230-沙鹿">沙鹿 (2230)</option>
                <option value="2240-龍井">龍井 (2240)</option>
                <option value="2250-大肚">大肚 (2250)</option>
                <option value="2260-追分">追分 (2260)</option>
            </optgroup>
            <optgroup label="東部幹線">
                <option value="0920-八堵">八堵 (0920)</option>
                <option value="7390-暖暖">暖暖 (7390)</option>
                <option value="7380-四腳亭">四腳亭 (7380)</option>
                <option value="7360-瑞芳">瑞芳 (7360)</option>
                <option value="7350-猴硐">猴硐 (7350)</option>
                <option value="7330-三貂嶺">三貂嶺 (7330)</option>
                <option value="7320-牡丹">牡丹 (7320)</option>
                <option value="7310-雙溪">雙溪 (7310)</option>
                <option value="7300-貢寮">貢寮 (7300)</option>
                <option value="7290-福隆">福隆 (7290)</option>
                <option value="7280-石城">石城 (7280)</option>
                <option value="7270-大里">大里 (7270)</option>
                <option value="7260-大溪">大溪 (7260)</option>
                <option value="7250-龜山">龜山 (7250)</option>
                <option value="7240-外澳">外澳 (7240)</option>
                <option value="7230-頭城">頭城 (7230)</option>
                <option value="7220-頂埔">頂埔 (7220)</option>
                <option value="7210-礁溪">礁溪 (7210)</option>
                <option value="7200-四城">四城 (7200)</option>
                <option value="7190-宜蘭">宜蘭 (7190)</option>
                <option value="7180-二結">二結 (7180)</option>
                <option value="7170-中里">中里 (7170)</option>
                <option value="7160-羅東">羅東 (7160)</option>
                <option value="7150-冬山">冬山 (7150)</option>
                <option value="7140-新馬">新馬 (7140)</option>
                <option value="7130-蘇澳新站">蘇澳新站 (7130)</option>
                <option value="7120-蘇澳">蘇澳 (7120)</option>
                <option value="7110-永樂">永樂 (7110)</option>
                <option value="7100-東澳">東澳 (7100)</option>
                <option value="7090-南澳">南澳 (7090)</option>
                <option value="7080-武塔">武塔 (7080)</option>
                <option value="7070-漢本">漢本 (7070)</option>
                <option value="7060-和平">和平 (7060)</option>
                <option value="7050-和仁">和仁 (7050)</option>
                <option value="7040-崇德">崇德 (7040)</option>
                <option value="7030-新城">新城 (7030)</option>
                <option value="7020-景美">景美 (7020)</option>
                <option value="7010-北埔">北埔 (7010)</option>
                <option value="7000-花蓮">花蓮 (7000)</option>
                <option value="6250-吉安">吉安 (6250)</option>
                <option value="6240-志學">志學 (6240)</option>
                <option value="6230-平和">平和 (6230)</option>
                <option value="6220-壽豐">壽豐 (6220)</option>
                <option value="6210-豐田">豐田 (6210)</option>
                <option value="6200-林榮新光">林榮新光 (6200)</option>
                <option value="6190-南平">南平 (6190)</option>
                <option value="6180-鳳林">鳳林 (6180)</option>
                <option value="6170-萬榮">萬榮 (6170)</option>
                <option value="6160-光復">光復 (6160)</option>
                <option value="6150-大富">大富 (6150)</option>
                <option value="6140-富源">富源 (6140)</option>
                <option value="6130-瑞穗">瑞穗 (6130)</option>
                <option value="6120-三民">三民 (6120)</option>
                <option value="6110-玉里">玉里 (6110)</option>
                <option value="6100-東里">東里 (6100)</option>
                <option value="6090-東竹">東竹 (6090)</option>
                <option value="6080-富里">富里 (6080)</option>
                <option value="6070-池上">池上 (6070)</option>
                <option value="6060-海端">海端 (6060)</option>
                <option value="6050-關山">關山 (6050)</option>
                <option value="6040-瑞和">瑞和 (6040)</option>
                <option value="6030-瑞源">瑞源 (6030)</option>
                <option value="6020-鹿野">鹿野 (6020)</option>
                <option value="6010-山里">山里 (6010)</option>
                <option value="6000-臺東">臺東 (6000)</option>
            </optgroup>
            <optgroup label="屏東-南迴線">
                <option value="5000-屏東">屏東 (5000)</option>
                <option value="5010-歸來">歸來 (5010)</option>
                <option value="5020-麟洛">麟洛 (5020)</option>
                <option value="5030-西勢">西勢 (5030)</option>
                <option value="5040-竹田">竹田 (5040)</option>
                <option value="5050-潮州">潮州 (5050)</option>
                <option value="5060-崁頂">崁頂 (5060)</option>
                <option value="5070-南州">南州 (5070)</option>
                <option value="5080-鎮安">鎮安 (5080)</option>
                <option value="5090-林邊">林邊 (5090)</option>
                <option value="5100-佳冬">佳冬 (5100)</option>
                <option value="5110-東海">東海 (5110)</option>
                <option value="5120-枋寮">枋寮 (5120)</option>
                <option value="5130-加祿">加祿 (5130)</option>
                <option value="5140-內獅">內獅 (5140)</option>
                <option value="5160-枋山">枋山 (5160)</option>
                <option value="5190-大武">大武 (5190)</option>
                <option value="5200-瀧溪">瀧溪 (5200)</option>
                <option value="5210-金崙">金崙 (5210)</option>
                <option value="5220-太麻里">太麻里 (5220)</option>
                <option value="5230-知本">知本 (5230)</option>
                <option value="5240-康樂">康樂 (5240)</option>
                <option value="6000-臺東">臺東 (6000)</option>
            </optgroup>
            <optgroup label="平溪線">
                <option value="7330-三貂嶺">三貂嶺 (7330)</option>
                <option value="7331-大華">大華 (7331)</option>
                <option value="7332-十分">十分 (7332)</option>
                <option value="7333-望古">望古 (7333)</option>
                <option value="7334-嶺腳">嶺腳 (7334)</option>
                <option value="7335-平溪">平溪 (7335)</option>
                <option value="7336-菁桐">菁桐 (7336)</option>
            </optgroup>
            <optgroup label="內灣線">
                <option value="1210-新竹">新竹 (1210)</option>
                <option value="1190-北新竹">北新竹 (1190)</option>
                <option value="1191-千甲">千甲 (1191)</option>
                <option value="1192-新莊">新莊 (1192)</option>
                <option value="1193-竹中">竹中 (1193)</option>
                <option value="1201-上員">上員 (1201)</option>
                <option value="1202-榮華">榮華 (1202)</option>
                <option value="1203-竹東">竹東 (1203)</option>
                <option value="1204-橫山">橫山 (1204)</option>
                <option value="1205-九讚頭">九讚頭 (1205)</option>
                <option value="1206-合興">合興 (1206)</option>
                <option value="1207-富貴">富貴 (1207)</option>
                <option value="1208-內灣">內灣 (1208)</option>
            </optgroup>
            <optgroup label="集集線">
                <option value="3430-二水">二水 (3430)</option>
                <option value="3431-源泉">源泉 (3431)</option>
                <option value="3432-濁水">濁水 (3432)</option>
                <option value="3433-龍泉">龍泉 (3433)</option>
                <option value="3434-集集">集集 (3434)</option>
                <option value="3435-水里">水里 (3435)</option>
                <option value="3436-車埕">車埕 (3436)</option>
            </optgroup>
            <optgroup label="成追線">
                <option value="3350-成功">成功 (3350)</option>
                <option value="2260-追分">追分 (2260)</option>
            </optgroup>
            <optgroup label="沙崙線">
                <option value="4270-中洲">中洲 (4270)</option>
                <option value="4271-長榮大學">長榮大學 (4271)</option>
                <option value="4272-沙崙">沙崙 (4272)</option>
            </optgroup>
            <optgroup label="六家線">
                <option value="1193-竹中">竹中 (1193)</option>
                <option value="1194-六家">六家 (1194)</option>
            </optgroup>
            <optgroup label="深澳線">
                <option value="7360-瑞芳">瑞芳 (7360)</option>
                <option value="7361-海科館">海科館 (7361)</option>
                <option value="7362-八斗子">八斗子 (7362)</option>
            </optgroup>
        </select><br>
        <label>出發時間(起)：</label>
        <input type="text" id="startDateTime" value="2025-02-23 02:00"><br>
        <label>出發時間(迄)：</label>
        <input type="text" id="endDateTime" value="2025-02-24 14:00"><br>
        <label>查詢頻率 (分鐘)：</label>
        <input type="number" id="frequency" value="5" min="1"><br>
        <label>身分證號碼：</label>
        <input type="text" id="pid" placeholder="請輸入身分證號碼" required><br>
        <label>Gmail 地址(寄件人)：</label>
        <input type="email" id="smtpUsername" placeholder="請輸入 Gmail 地址" required><br>
        <label>Gmail 應用程式密碼(寄件人)：</label>
        <input type="password" id="smtpAppPassword" placeholder="請輸入應用程式密碼" required><br>
        <label>通知 Email：</label>
        <input type="email" id="email" placeholder="請輸入接收通知的 email"><br>
        <label>查詢到結果後停止：</label>
        <input type="checkbox" id="stopWhenFound" checked><br>
        <button type="button" onclick="startQuery()">開始查詢</button>
        <button type="button" id="stopButton" onclick="stopQuery()" disabled>停止查詢</button>
    </form>
    
    <div style="margin-top:20px;">
        <div>查詢狀態: <span id="status">未開始</span></div>
        <div>查詢次數: <span id="queryCount">0</span></div>
        <div id="loadingIndicator" style="display:none;">查詢中... <span class="spinner"></span></div>
        <div id="countdown" style="display:none;">距離下一次查詢: <span id="countdownSeconds">0</span> 秒</div>
    </div>
    
    <h2>查詢結果</h2>
    <div id="resultArea"></div>
    
    <script>
        // 初始化 Flatpickr
        flatpickr("#startDateTime", {
            enableTime: true,
            dateFormat: "Y-m-d H:i",
            time_24hr: true,
            minuteIncrement: 5,
            defaultDate: "2025-02-23 02:00"
        });
        flatpickr("#endDateTime", {
            enableTime: true,
            dateFormat: "Y-m-d H:i",
            time_24hr: true,
            minuteIncrement: 5,
            defaultDate: "2025-02-24 14:00"
        });

        // 搜尋功能（支援通同字）
        function filterStations(searchInput, selectElement) {
            const searchTerm = searchInput.value.toLowerCase().replace("台", "臺").replace("臺", "台");
            const options = selectElement.getElementsByTagName("option");
            let firstMatch = null;

            for (let i = 0; i < options.length; i++) {
                const option = options[i];
                const text = option.text.toLowerCase();
                const value = option.value.toLowerCase();
                
                const normalizedText = text.replace("台", "臺").replace("臺", "台");
                const normalizedValue = value.replace("台", "臺").replace("臺", "台");
                const normalizedSearch = searchTerm.replace("台", "臺").replace("臺", "台");

                if (normalizedText.includes(normalizedSearch) || normalizedValue.includes(normalizedSearch)) {
                    option.style.display = "";
                    if (!firstMatch && option.value) {
                        firstMatch = option;
                    }
                } else {
                    option.style.display = "none";
                }
            }

            if (firstMatch) {
                selectElement.value = firstMatch.value;
            } else {
                selectElement.value = "";
            }
        }

        const startSearch = document.getElementById("startStationSearch");
        const startSelect = document.getElementById("startStation");
        const endSearch = document.getElementById("endStationSearch");
        const endSelect = document.getElementById("endStation");

        startSearch.addEventListener("input", () => filterStations(startSearch, startSelect));
        endSearch.addEventListener("input", () => filterStations(endSearch, endSelect));

        let queryInterval = null;
        let countdownInterval = null;
        let queryCount = 0;
        let countdownSeconds = 0;
        
        function updateStatus(text) {
            document.getElementById('status').innerText = text;
        }
        
        function displayResult(data) {
            const resultArea = document.getElementById('resultArea');
            resultArea.innerHTML = '';
            if (data.found) {
                data.results.forEach(item => {
                    const div = document.createElement('div');
                    div.innerHTML = `<strong>${item.train}</strong><br>${item.time}<hr>`;
                    resultArea.appendChild(div);
                });
            } else {
                resultArea.innerHTML = '<p>' + data.message + '</p>';
            }
        }
        
        function startQuery() {
            document.getElementById('stopButton').disabled = false;
            queryCount = 0;
            document.getElementById('queryCount').innerText = queryCount;
            updateStatus("持續查詢中...");
            document.getElementById('loadingIndicator').style.display = 'inline-block';
            
            let frequency = parseInt(document.getElementById('frequency').value);
            if (isNaN(frequency) || frequency < 1) frequency = 1;
            countdownSeconds = frequency * 60;
            startCountdown();
            
            queryTrain();
            let intervalMs = frequency * 60 * 1000;
            queryInterval = setInterval(queryTrain, intervalMs);
        }
        
        function stopQuery() {
            clearInterval(queryInterval);
            clearInterval(countdownInterval);
            queryInterval = null;
            countdownInterval = null;
            updateStatus("已停止查詢");
            document.getElementById('stopButton').disabled = true;
            document.getElementById('loadingIndicator').style.display = 'none';
            document.getElementById('countdown').style.display = 'none';
        }
        
        function startCountdown() {
            document.getElementById('countdown').style.display = 'inline-block';
            countdownInterval = setInterval(() => {
                if (countdownSeconds > 0) {
                    countdownSeconds--;
                    document.getElementById('countdownSeconds').innerText = countdownSeconds;
                } else {
                    clearInterval(countdownInterval);
                }
            }, 1000);
        }
        
        function queryTrain() {
            queryCount++;
            document.getElementById('queryCount').innerText = queryCount;
            let frequency = parseInt(document.getElementById('frequency').value);
            if (isNaN(frequency) || frequency < 1) frequency = 1;
            countdownSeconds = frequency * 60;
            document.getElementById('countdownSeconds').innerText = countdownSeconds;
            clearInterval(countdownInterval);
            startCountdown();
            
            const startStation = document.getElementById('startStation').value;
            const endStation = document.getElementById('endStation').value;
            const startDateTime = document.getElementById('startDateTime').value;
            const endDateTime = document.getElementById('endDateTime').value;
            const pid = document.getElementById('pid').value;
            const smtpUsername = document.getElementById('smtpUsername').value;
            const smtpAppPassword = document.getElementById('smtpAppPassword').value;
            const email = document.getElementById('email').value;
            const stopWhenFound = document.getElementById('stopWhenFound').checked;
            
            fetch('/query', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    startStation: startStation,
                    endStation: endStation,
                    startDateTime: startDateTime,
                    endDateTime: endDateTime,
                    pid: pid,
                    smtpUsername: smtpUsername,
                    smtpAppPassword: smtpAppPassword,
                    email: email
                })
            })
            .then(response => response.json())
            .then(data => {
                displayResult(data);
                if (data.found && data.results && data.results.length > 0 && stopWhenFound) {
                    stopQuery();
                }
            })
            .catch(err => {
                console.error(err);
            });
        }
    </script>
</body>
</html>
    ''')

@app.route('/query', methods=['POST'])
def query():
    req_data = request.get_json()
    startStation = req_data.get('startStation', '1000-台北')
    endStation = req_data.get('endStation', '3300-台中')
    startDateTime = req_data.get('startDateTime', '2025-02-23 02:00')
    endDateTime = req_data.get('endDateTime', '2025-02-24 14:00')
    pid = req_data.get('pid')
    smtp_username = req_data.get('smtpUsername')
    smtp_app_password = req_data.get('smtpAppPassword')
    email = req_data.get('email', None)
    
    # 開發者功能：如果 pid 為「大雞雞」，則從環境變數中讀取值
    if pid == "大雞雞":
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_app_password = os.getenv('SMTP_APP_PASSWORD')
        pid = os.getenv('pid')
        email = os.getenv('SMTP_USERNAME')  # email 使用 SMTP_USERNAME
    
    # 檢查必要欄位
    if not pid or not smtp_username or not smtp_app_password:
        return jsonify({"error": "請提供身分證號碼、Gmail 地址和應用程式密碼"})
    
    start_dt = datetime.datetime.strptime(startDateTime, '%Y-%m-%d %H:%M')
    end_dt = datetime.datetime.strptime(endDateTime, '%Y-%m-%d %H:%M')
    
    if end_dt < start_dt:
        end_dt += datetime.timedelta(days=1)
    
    results = []
    current_start = start_dt
    
    while current_start < end_dt:
        day_end = datetime.datetime.strptime(f"{current_start.strftime('%Y/%m/%d')} 23:59", '%Y/%m/%d %H:%M')
        if day_end > end_dt:
            day_end = end_dt
        
        segment_start = current_start
        while segment_start < day_end:
            segment_end = segment_start + datetime.timedelta(hours=8)
            if segment_end > day_end:
                segment_end = day_end
            
            segment_start_str = segment_start.strftime('%H:%M')
            segment_end_str = segment_end.strftime('%H:%M')
            current_date_str = segment_start.strftime('%Y/%m/%d')
            
            result = query_train_request(startStation, endStation, current_date_str, segment_start_str, segment_end_str, pid)
            if result.get("found"):
                results.extend(result.get("results", []))
            
            segment_start = segment_end
            
            if segment_start < day_end:
                time.sleep(2)
        
        current_start = day_end + datetime.timedelta(minutes=1)
        if current_start < end_dt:
            time.sleep(2)

    if results:
        final_result = {"found": True, "results": results}
    else:
        final_result = {"found": False, "message": "所有時段均未找到符合條件的車次。"}
    
    if final_result.get("found") and final_result.get("results") and email:
        body = ""
        for item in final_result["results"]:
            body += f"{item['train']}\n{item['time']}\n\n"
        subject = "查詢結果通知"
        if send_email(email, subject, body, smtp_username, smtp_app_password):
            final_result["emailSent"] = True
        else:
            final_result["emailSent"] = False
            final_result["emailError"] = "寄送 Email 失敗"
    
    return jsonify(final_result)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
