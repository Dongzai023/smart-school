import requests
import json
import uuid

BASE_URL = "http://localhost:8002"
TEST_ADMIN = {
    "employee_id": "QJ202309001",
    "password": "123456"
}

def test_admin_users_api():
    print("🚀 Starting Admin Users API Tests...")
    
    # 1. Login as Admin
    print("\n--- 1. Testing Login ---")
    login_url = f"{BASE_URL}/api/auth/login"
    response = requests.post(login_url, json=TEST_ADMIN)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return
    
    token = response.json()["access_token"]
    print("✅ Login successful")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Generate unique employee ID for testing
    test_emp_id = f"TEST_{str(uuid.uuid4())[:8]}"

    # 2. Add a new user
    print(f"\n--- 2. Add new user ({test_emp_id}) ---")
    add_url = f"{BASE_URL}/api/admin/users"
    new_user_data = {
        "employee_id": test_emp_id,
        "name": "测试教师",
        "gender": "男",
        "phone": "13800138000",
        "teaching_subject": "数学",
        "department_group": "理科组",
        "department": "高中部",
        "grade": "高一",
        "class_name": "1班"
    }
    response = requests.post(add_url, json=new_user_data, headers=headers)
    if response.status_code != 201:
        print(f"❌ Add user failed: {response.text}")
        return
    
    created_user = response.json()
    user_id = created_user["id"]
    print(f"✅ User added successfully: ID={user_id}, Name={created_user['name']}")
    
    # 3. Get user list (Search by new user's name)
    print("\n--- 3. Query user list ---")
    query_url = f"{BASE_URL}/api/admin/users?search=测试教师"
    response = requests.get(query_url, headers=headers)
    if response.status_code == 200:
        users = response.json()
        print(f"✅ Users found: {len(users)}")
    else:
        print(f"❌ Query users failed: {response.text}")
        
    # 4. Modify user details
    print(f"\n--- 4. Modify user (ID={user_id}) ---")
    update_url = f"{BASE_URL}/api/admin/users/{user_id}"
    update_data = {
        "class_name": "实验2班",
        "grade": "高二"
    }
    response = requests.put(update_url, json=update_data, headers=headers)
    if response.status_code == 200:
        updated_user = response.json()
        print(f"✅ User modified successfully: Grade={updated_user['grade']}, Class={updated_user['class_name']}")
    else:
        print(f"❌ Modify user failed: {response.text}")

    # 5. Get single user details
    print(f"\n--- 5. Get single user details (ID={user_id}) ---")
    get_url = f"{BASE_URL}/api/admin/users/{user_id}"
    response = requests.get(get_url, headers=headers)
    if response.status_code == 200:
        user_detail = response.json()
        print(f"✅ Got user details: Subject={user_detail['teaching_subject']}, Phone={user_detail['phone']}")
    else:
        print(f"❌ Get user details failed: {response.text}")

    # 6. Delete the user
    print(f"\n--- 6. Delete user (ID={user_id}) ---")
    delete_url = f"{BASE_URL}/api/admin/users/{user_id}"
    response = requests.delete(delete_url, headers=headers)
    if response.status_code == 200:
        print(f"✅ User deleted successfully.")
    else:
        print(f"❌ Delete user failed: {response.text}")
        
    print("\n🎉 All Admin API tests completed!")

if __name__ == "__main__":
    try:
        test_admin_users_api()
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        print("💡 Is the backend server running?")
