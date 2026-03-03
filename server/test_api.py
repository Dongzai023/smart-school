import requests
import json
import time

BASE_URL = "http://localhost:8001"
TEST_USER = {
    "employee_id": "QJ202309001",
    "password": "123456"
}

def test_backend_api():
    print("🚀 Starting Backend API Tests...")
    
    # 1. Login
    print("\n--- 1. Testing Login ---")
    login_url = f"{BASE_URL}/api/auth/login"
    response = requests.post(login_url, json=TEST_USER)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return
    
    data = response.json()
    token = data["access_token"]
    print("✅ Login successful")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get User Info
    print("\n--- 2. Testing User Info (/api/users/me) ---")
    me_url = f"{BASE_URL}/api/users/me"
    response = requests.get(me_url, headers=headers)
    if response.status_code == 200:
        print(f"✅ User Info: {response.json()['name']} ({response.json()['employee_id']})")
    else:
        print(f"❌ Failed to get user info: {response.text}")

    # 3. Get Today Schedule
    print("\n--- 3. Testing Today Schedule (/api/checkin/today) ---")
    schedule_url = f"{BASE_URL}/api/checkin/today"
    response = requests.get(schedule_url, headers=headers)
    if response.status_code == 200:
        items = response.json().get("items", [])
        print(f"✅ Today's slots found: {len(items)}")
        for item in items:
            print(f"   - {item['time_slot']['label']}: {item['status']}")
    else:
        print(f"❌ Failed to get schedule: {response.text}")

    # 4. Get Statistics Overview
    print("\n--- 4. Testing Stats Overview (/api/statistics/overview) ---")
    stats_url = f"{BASE_URL}/api/statistics/overview?period=week"
    response = requests.get(stats_url, headers=headers)
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Attendance Rate: {stats['attendance_rate']}%")
        print(f"✅ Rank: #{stats['school_rank']} ({stats['rank_label']})")
    else:
        print(f"❌ Failed to get stats: {response.text}")

    # 5. Get Achievements
    print("\n--- 5. Testing Achievements (/api/achievements) ---")
    ach_url = f"{BASE_URL}/api/achievements"
    response = requests.get(ach_url, headers=headers)
    if response.status_code == 200:
        ach = response.json()
        print(f"✅ Unlocked: {ach['unlocked_count']}/{ach['total_count']}")
    else:
        print(f"❌ Failed to get achievements: {response.text}")

    # 6. Get Recent Records
    print("\n--- 6. Testing Recent Records (/api/statistics/records) ---")
    records_url = f"{BASE_URL}/api/statistics/records?limit=5"
    response = requests.get(records_url, headers=headers)
    if response.status_code == 200:
        records = response.json().get("records", [])
        print(f"✅ Recent days records found: {len(records)}")
    else:
        print(f"❌ Failed to get records: {response.text}")

    print("\n🎉 All backend API tests completed!")

if __name__ == "__main__":
    try:
        test_backend_api()
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        print("💡 Is the backend server running at http://localhost:8001?")
