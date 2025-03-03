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
    enableEmail = req_data.get('enableEmail', False)
    smtpUsername = req_data.get('smtpUsername', '')
    smtpAppPassword = req_data.get('smtpAppPassword', '')
    email = req_data.get('email', '')

    if pid == "大雞雞":
        smtpUsername = os.getenv('SMTP_USERNAME')
        smtpAppPassword = os.getenv('SMTP_APP_PASSWORD')
        pid = os.getenv('pid')
        email = os.getenv('SMTP_USERNAME')

    if not pid:
        return jsonify({"error": "請提供身分證號碼"})

    try:
        start_dt = datetime.datetime.strptime(startDateTime, '%Y-%m-%d %H:%M')
        end_dt = datetime.datetime.strptime(endDateTime, '%Y-%m-%d %H:%M')
    except ValueError:
        return jsonify({"error": "日期時間格式錯誤，請使用 YYYY-MM-DD HH:MM"})

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
            
            try:
                result = query_train_request(startStation, endStation, current_date_str, segment_start_str, segment_end_str, pid)
                if result.get("found"):
                    results.extend(result.get("results", []))
            except Exception as e:
                return jsonify({"error": f"查詢火車資料失敗: {str(e)}"})
            
            segment_start = segment_end
            if segment_start < day_end:
                time.sleep(2)
        
        current_start = day_end + datetime.timedelta(minutes=1)
        if current_start < end_dt:
            time.sleep(2)

    if results:
        final_result = {"found": True, "results": results}
        if enableEmail and email and smtpUsername and smtpAppPassword:
            body = ""
            for item in final_result["results"]:
                body += f"{item['train']}\n{item['time']}\n\n"
            subject = "查詢結果通知"
            try:
                if send_email(email, subject, body, smtpUsername, smtpAppPassword):
                    final_result["emailSent"] = True
                else:
                    final_result["emailSent"] = False
                    final_result["emailError"] = "寄送 Email 失敗"
            except Exception as e:
                final_result["emailSent"] = False
                final_result["emailError"] = f"寄送 Email 失敗: {str(e)}"
    else:
        final_result = {"found": False, "message": "所有時段均未找到符合條件的車次。"}
    
    return jsonify(final_result)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)