from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from typing import List, Dict, Optional
import json
import tempfile
from datetime import datetime
from uuid import uuid4

# Load environment variables
load_dotenv()

app = FastAPI(title="ChatPDF")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Estrutura para armazenar sessões
class Session:
    def __init__(self, id: str, title: str = "Nova Conversa"):
        self.id = id
        self.title = title
        self.pdfs = []
        self.messages = []
        self.conversation = None
        self.last_activity = datetime.now()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "pdfs": [{"name": pdf["name"]} for pdf in self.pdfs],
            "pdf_count": len(self.pdfs),
            "message_count": len(self.messages),
            "last_activity": self.last_activity.isoformat()
        }

    def add_pdf(self, pdf_name: str, text: str):
        self.pdfs.append({"name": pdf_name, "text": text})
        self.last_activity = datetime.now()

    def remove_pdf(self, pdf_name: str):
        self.pdfs = [pdf for pdf in self.pdfs if pdf["name"] != pdf_name]
        self.last_activity = datetime.now()
        return len(self.pdfs)

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.last_activity = datetime.now()

# Global variables
sessions: Dict[str, Session] = {}
current_session: Optional[str] = None

def get_current_session() -> Session:
    """Get current session or create a new one."""
    global current_session, sessions
    if not current_session or current_session not in sessions:
        new_session = Session(str(uuid4()))
        sessions[new_session.id] = new_session
        current_session = new_session.id
    return sessions[current_session]

def process_pdf(pdf_path: str) -> str:
    """Extract text from PDF."""
    try:
        pdf_reader = PdfReader(pdf_path)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")

def create_conversation_chain(texts: List[str], session: Session):
    """Create or update conversation chain with new texts."""
    try:
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = []
        for text in texts:
            chunks.extend(text_splitter.split_text(text))

        if not chunks:
            raise HTTPException(status_code=400, detail="Não foi possível extrair texto dos PDFs")

        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_texts(texts=chunks, embedding=embeddings)
        
        memory = ConversationBufferMemory(
            memory_key='chat_history',
            output_key='answer',
            return_messages=True,
            input_key='question'
        )
        
        session.conversation = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(temperature=0.7),
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            memory=memory,
            chain_type="stuff",
            return_source_documents=True,
            verbose=True
        )
        # Inicializar o chat em português
        session.conversation({"question": "Por favor, sempre responda em português do Brasil de forma natural e amigável."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar cadeia de conversação: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page."""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/sessions")
async def create_session(request: Request):
    """Create a new session."""
    try:
        body = await request.json()
        title = body.get("title", "Nova Conversa")
        session = Session(str(uuid4()), title)
        sessions[session.id] = session
        return {
            "id": session.id,
            "title": session.title,
            "created_at": session.last_activity.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar sessão: {str(e)}")

@app.get("/sessions")
async def list_sessions():
    """List all sessions."""
    return {
        "sessions": [session.to_dict() for session in sessions.values()]
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        del sessions[session_id]
        return {"message": "Sessão excluída com sucesso"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao excluir sessão: {str(e)}")

@app.put("/sessions/{session_id}/title")
async def update_session_title(session_id: str, request: Request):
    """Update session title."""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        data = await request.json()
        title = data.get("title")
        
        if not title:
            raise HTTPException(status_code=400, detail="Título é obrigatório")
        
        sessions[session_id].title = title
        return sessions[session_id].to_dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar título: {str(e)}")

@app.post("/sessions/{session_id}/select")
async def select_session(session_id: str):
    """Select a session as current."""
    global current_session
    if session_id in sessions:
        current_session = session_id
        return {"message": "Sessão selecionada com sucesso"}
    raise HTTPException(status_code=404, detail="Sessão não encontrada")

@app.delete("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """Clear session data."""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        session = sessions[session_id]
        session.conversation = None
        session.pdfs = []
        session.messages = []
        
        return {"message": "Sessão limpa com sucesso"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar sessão: {str(e)}")

@app.post("/upload")
async def upload_pdfs(files: List[UploadFile] = File(...), session_id: str = Form(...)):
    """Handle multiple PDF uploads for a session."""
    try:
        if session_id not in sessions:
            return {"error": "Sessão inválida"}

        session = sessions[session_id]
        
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                return {"error": "Por favor, envie apenas arquivos PDF"}

            content = await file.read()
            
            # Salvar arquivo temporariamente
            temp_path = f"temp_{file.filename}"
            with open(temp_path, "wb") as f:
                f.write(content)
            
            try:
                text = process_pdf(temp_path)
                if not text.strip():
                    return {"error": f"Não foi possível extrair texto do arquivo {file.filename}"}
                    
                session.add_pdf(file.filename, text)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # Criar ou atualizar a cadeia de conversação
        texts = [pdf["text"] for pdf in session.pdfs]
        create_conversation_chain(texts, session)

        return {
            "message": "PDFs processados com sucesso",
            "session": session.to_dict()
        }

    except Exception as e:
        print(f"Erro no upload: {str(e)}")
        return {"error": str(e)}

@app.post("/chat")
async def chat_endpoint(request: Request):
    """Handle chat messages."""
    try:
        data = await request.json()
        message = data.get("message", "")
        session_id = data.get("session_id")

        if not session_id or session_id not in sessions:
            return {"error": "Sessão inválida"}

        session = sessions[session_id]
        
        if not session.pdfs:
            return {"error": "Por favor, faça upload de pelo menos um PDF antes de iniciar o chat"}

        session.add_message("user", message)
        
        if not session.conversation:
            texts = [pdf["text"] for pdf in session.pdfs]
            create_conversation_chain(texts, session)

        response = session.conversation({"question": message})
        ai_message = response.get("answer", "Desculpe, não consegui processar sua pergunta.")
        
        session.add_message("assistant", ai_message)
        
        return {
            "response": ai_message,
            "session": session.to_dict()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar mensagem: {str(e)}")

@app.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get all messages from a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    return {"messages": sessions[session_id].messages}

@app.get("/sessions/{session_id}/pdfs")
async def get_session_pdfs(session_id: str):
    """Get list of PDFs in a session."""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        session = sessions[session_id]
        return {
            "files": [{"name": pdf["name"]} for pdf in session.pdfs],
            "session": session.to_dict()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter PDFs: {str(e)}")

@app.delete("/sessions/{session_id}/pdfs/{pdf_name}")
async def delete_pdf(session_id: str, pdf_name: str):
    """Delete a PDF from a session."""
    try:
        if session_id not in sessions:
            return {"error": "Sessão inválida"}

        session = sessions[session_id]
        remaining_pdfs = session.remove_pdf(pdf_name)
        
        # Se ainda houver PDFs, recria a cadeia de conversação
        if remaining_pdfs > 0:
            texts = [pdf["text"] for pdf in session.pdfs]
            create_conversation_chain(texts, session)
        else:
            session.conversation = None
        
        return {"message": "PDF excluído", "session": session.to_dict()}

    except Exception as e:
        print(f"Erro ao excluir PDF: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)
