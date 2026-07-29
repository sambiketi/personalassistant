import re

# Read the file
with open('routes.py', 'r') as f:
    content = f.read()

# Find the progress endpoint
start = content.find('@router.get("/progress/{user_id}")')

if start != -1:
    # Find the end of this function (next @router or end of file)
    end = content.find('@router.', start + 10)
    if end == -1:
        end = len(content)
    
    # New replacement
    replacement = '''@router.get("/progress/{user_id}")
async def get_progress(user_id: str):
    """Get user progress"""
    try:
        user = db.get_or_create_user(user_id)
        agent = get_agent(user_id)
        response = agent.handle_show_progress()
        
        vanguard_data = None
        try:
            if agent and hasattr(agent, 'vanguard_brain') and agent.vanguard_brain:
                vanguard_data = agent.vanguard_brain.get_stats()
        except:
            pass
        
        return {
            "success": True,
            "progress": response.message if response else "No progress data available",
            "vanguard": vanguard_data
        }
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        return {
            "success": False,
            "progress": "Unable to load progress data",
            "vanguard": None
        }
'''
    
    # Replace
    new_content = content[:start] + replacement + content[end:]
    
    with open('routes.py', 'w') as f:
        f.write(new_content)
    
    print('✅ Progress endpoint updated!')
else:
    print('❌ Could not find progress endpoint')
