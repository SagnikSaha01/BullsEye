Requirements:
Python version (not sure if this matters): 3.13.5
- Type **python --version** to check this

Setup instructions
1. Clone repo
2. cd into **backend** file
3. type **python -m venv venv**
4. type **venv\Scripts\activate** (windows) OR **source venv/bin/activate** (mac)
- Ensure your virtual enviornment is active in vscode terminal by making sure it looks like this
  
![image](https://github.com/user-attachments/assets/b1249c70-de52-4345-96e0-37bbc16170fb)

5. type **pip install -r requirements.txt**
6. type **uvicorn main:app --reload**
- Should see a message that says "Uvicorn running on _____"
- Click the link and make sure there is a json that says {"message":"Hello World"}
7. Open git bash and type **git checkout {your_name}/api-endpoint** to switch to your branch
8. profit
