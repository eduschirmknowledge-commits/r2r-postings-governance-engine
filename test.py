from dotenv import load_dotenv
load_dotenv()

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash")
    print("Gemini OK:", llm.invoke("Say hi").content)
except Exception as e:
    print("Gemini FAILED:", e)

try:
    from langchain_groq import ChatGroq
    llm = ChatGroq(model="  ")
    print("Groq OK:", llm.invoke("Say hi").content)
except Exception as e:
    print("Groq FAILED:", e)