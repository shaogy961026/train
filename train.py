from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# 設置 Gmail SMTP 參數（不再使用環境變數）
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def get_token(session, url, token_name):
    """
    從指定 URL 的 HTML 中取得指定名稱的 token 值
    """
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
        ("pid", pid),  # 使用前端傳來的 pid
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
            else:
                train_info = "未知車次"
            tds = row.find_all("td")
            if len(tds) >= 4:
                departure_time = tds[2].get_text(strip=True)
                arrival_time = tds[3].get_text(strip=True)
                time_info = f"{departure_time}-{arrival_time}"
            else:
                time_info = "未知時間"
            results.append({"train": train_info, "time": time_info})
        return {"found": True, "results": results}
    else:
        warning = soup.find("h2", class_="icon-fa warning")
        if warning:
            return {"found": False, "message": "您所查詢的條件，均沒有空位。"}
        else:
            return {"found": False, "message": "未找到明確的查詢結果。"}

def send_email(recipient, subject, body, smtp_username, smtp_app_password):
    """
    使用前端傳來的 Gmail 帳號和應用程式密碼寄送 Email
    """
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
    </style>
</head>
<body>
    <h1>台鐵查詢系統</h1>
    <h1>輸入請參考 https://www.railway.gov.tw/tra-tip-web/tip/tip001/tip123/query</h1>
    <form id="queryForm">
        <label>起始車站：</label>
        <input type="text" id="startStation" value="1000-台北"><br>
        <label>抵達站：</label>
        <input type="text" id="endStation" value="3300-台中"><br>
        <label>日期：</label>
        <input type="date" id="rideDate" value="2025-02-28"><br>
        <label>出發時間(起始時間)：</label>
        <input type="time" id="startTime" value="12:00"><br>
        <label>出發時間(結束時間)：</label>
        <input type="time" id="endTime" value="13:00"><br>
        <label>查詢頻率 (分鐘)：</label>
        <input type="number" id="frequency" value="5" min="1"><br>
        <label>身分證號碼：</label>
        <input type="text" id="pid" placeholder="請輸入身分證號碼" required><br>
        <label>Gmail 地址(寄件人)：</label>
        <input type="email" id="smtpUsername" placeholder="請輸入 Gmail 地址" required><br>
        <label>Gmail 應用程式密碼(寄件人)：</label>
        <input type="password" id="smtpAppPassword" placeholder="請輸入應用程式密碼" required><br>
        <label>通知 Email：</label>
        <input type="email(收件人)" id="email" placeholder="請輸入接收通知的 email"><br>
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
            if(data.found) {
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
            const rideDate = document.getElementById('rideDate').value;
            const startTime = document.getElementById('startTime').value;
            const endTime = document.getElementById('endTime').value;
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
                    rideDate: rideDate,
                    startTime: startTime,
                    endTime: endTime,
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
    rideDate = req_data.get('rideDate', '2025/02/28')
    if '-' in rideDate:
        rideDate = rideDate.replace('-', '/')
    startTime = req_data.get('startTime', '12:00')
    endTime = req_data.get('endTime', '13:00')
    pid = req_data.get('pid')  # 從前端獲取
    smtp_username = req_data.get('smtpUsername')  # 從前端獲取
    smtp_app_password = req_data.get('smtpAppPassword')  # 從前端獲取
    email = req_data.get('email', None)
    
    # 檢查必要欄位
    if not pid or not smtp_username or not smtp_app_password:
        return jsonify({"error": "請提供身分證號碼、Gmail 地址和應用程式密碼"})
    
    result = query_train_request(startStation, endStation, rideDate, startTime, endTime, pid)
    
    # 如果有查到結果且有提供 email，寄送通知
    if result.get("found") and result.get("results") and email:
        body = ""
        for item in result["results"]:
            body += f"{item['train']}\n{item['time']}\n\n"
        subject = "查詢結果通知"
        if send_email(email, subject, body, smtp_username, smtp_app_password):
            result["emailSent"] = True
        else:
            result["emailSent"] = False
            result["emailError"] = "寄送 Email 失敗"
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
