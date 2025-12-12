# test_phi3.py
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="phi3",
    base_url="http://localhost:11434",
    temperature=0.0,
)

resp = llm.invoke("Diga um resumo de 2 linhas sobre o Ceará")
print(resp.content)
