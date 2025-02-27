from flask import Flask, render_template, request, jsonify
from utils.query import query_train_request
from utils.email import send_email
import datetime
import time
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

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
        email = os.getenv('SMTP_USERNAME')
    
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