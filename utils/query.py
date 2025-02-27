import requests
from bs4 import BeautifulSoup

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