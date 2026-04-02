import { useState, useCallback, useEffect } from 'react'
import Sidebar from '../components/Sidebar/Sidebar'
import ChatWindow from '../components/ChatWindow/ChatWindow'
import AuthModal from '../components/AuthModal/AuthModal'
import './ChatPage.css'

// Simulated AI response (will be replaced by backend API call)
const simulateAIResponse = async (message) => {
    await new Promise((resolve) => setTimeout(resolve, 1200 + Math.random() * 800))

    const responses = {
        default: `Thank you for your question about "${message.slice(0, 40)}..."

I'd be happy to help with that. Here are some key points:

- **Always consult your pharmacist** or doctor before starting any new medication
- **Drug interactions** can vary based on individual health conditions
- **Dosage guidelines** should be followed as prescribed

⚠️ This is a demo response. Once connected to the backend, I'll provide accurate, evidence-based pharmaceutical information from verified drug databases.

Would you like to know more about a specific medication?`,

        'metformin': `**Metformin** is one of the most commonly prescribed medications for **Type 2 Diabetes**.

**Common Side Effects:**
- Nausea and stomach upset (usually temporary)
- Diarrhea
- Metallic taste in mouth
- Reduced appetite

**Serious Side Effects (seek medical attention):**
- Lactic acidosis (rare but serious)
- Severe allergic reactions
- Unusual muscle pain or weakness

**Key Information:**
- Take with food to minimize stomach upset
- Avoid excessive alcohol consumption
- Regular kidney function monitoring recommended
- Do not crush extended-release tablets

⚠️ Warning: Metformin should be temporarily discontinued before certain medical procedures involving contrast dye.`,

        'ibuprofen': `**Ibuprofen** is a nonsteroidal anti-inflammatory drug (NSAID) used for pain, inflammation, and fever.

**Common Side Effects:**
- Stomach upset or pain
- Nausea
- Dizziness
- Headache

**Drug Interactions to watch:**
- **Blood thinners** (warfarin, aspirin) — increased bleeding risk
- **ACE inhibitors** — reduced blood pressure effect
- **Lithium** — increased lithium levels
- **Other NSAIDs** — increased side effect risk

**Recommended Dosage (Adults):**
- 200–400mg every 4–6 hours as needed
- Maximum: 1200mg/day (OTC) or 3200mg/day (prescription)

⚠️ Warning: Long-term use may increase risk of heart attack, stroke, and gastrointestinal bleeding.`,

        'allergies': `For **seasonal allergies**, here are some effective OTC options:

**Antihistamines (Non-drowsy):**
- **Cetirizine** (Zyrtec) — once daily, fast-acting
- **Loratadine** (Claritin) — once daily, minimal drowsiness
- **Fexofenadine** (Allegra) — once daily, least sedating

**Nasal Sprays:**
- **Fluticasone** (Flonase) — steroid spray, very effective
- **Cromolyn sodium** (NasalCrom) — mast cell stabilizer

**Eye Drops:**
- **Ketotifen** (Zaditor) — antihistamine eye drops for itchy eyes

**Tips:**
- Start medications before allergy season begins
- Nasal sprays work best with consistent daily use
- Combine an antihistamine with a nasal spray for severe symptoms

Would you like more details about any of these options?`,

        'amoxicillin': `**Amoxicillin** is a penicillin-type antibiotic used to treat bacterial infections.

**Standard Adult Dosage:**
- **Mild infections:** 250mg every 8 hours or 500mg every 12 hours
- **Moderate/severe:** 500mg every 8 hours or 875mg every 12 hours
- **Duration:** Typically 7–14 days depending on infection

**Common Side Effects:**
- Diarrhea
- Nausea
- Skin rash
- Headache

**Important Notes:**
- Complete the full course even if feeling better
- Can be taken with or without food
- Store suspension in refrigerator
- May reduce effectiveness of oral contraceptives

⚠️ Warning: Tell your doctor if you have a penicillin or cephalosporin allergy before taking amoxicillin.`,
    }

    const lowerMsg = message.toLowerCase()
    if (lowerMsg.includes('metformin')) return responses.metformin
    if (lowerMsg.includes('ibuprofen') || lowerMsg.includes('blood thinner')) return responses.ibuprofen
    if (lowerMsg.includes('allerg')) return responses.allergies
    if (lowerMsg.includes('amoxicillin') || lowerMsg.includes('dosage') || lowerMsg.includes('dose')) return responses.amoxicillin
    return responses.default
}

function ChatPage() {
    const [conversations, setConversations] = useState([])
    const [activeConversationId, setActiveConversationId] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [showAuthModal, setShowAuthModal] = useState(false)
    const [authMode, setAuthMode] = useState('login')
    const [user, setUser] = useState(null)

    const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

    // Check if user is already logged in on mount
    useEffect(() => {
        const checkAuth = async () => {
            try {
                const res = await fetch(`${API}/auth/me/`, { credentials: 'include' })
                const data = await res.json()
                if (data.id) setUser(data)
            } catch { /* not logged in */ }
        }
        checkAuth()
    }, [API])

    const handleShowAuth = (mode = 'login') => {
        setAuthMode(mode)
        setShowAuthModal(true)
    }

    const handleLogout = async () => {
        try {
            await fetch(`${API}/auth/logout/`, {
                method: 'POST',
                credentials: 'include',
            })
        } catch { /* ignore */ }
        setUser(null)
    }

    const activeConversation = conversations.find((c) => c.id === activeConversationId)
    const messages = activeConversation?.messages || []

    const createConversation = useCallback((firstMessage) => {
        const id = Date.now().toString()
        const title = firstMessage.length > 35 ? firstMessage.slice(0, 35) + '...' : firstMessage
        const newConv = { id, title, messages: [] }
        setConversations((prev) => [newConv, ...prev])
        setActiveConversationId(id)
        return id
    }, [])

    const handleSendMessage = useCallback(async (text) => {
        let convId = activeConversationId

        if (!convId) {
            convId = createConversation(text)
        }

        const userMsg = {
            role: 'user',
            content: text,
            timestamp: new Date().toISOString(),
        }

        setConversations((prev) =>
            prev.map((c) =>
                c.id === convId ? { ...c, messages: [...c.messages, userMsg] } : c
            )
        )

        setIsLoading(true)

        try {
            const aiText = await simulateAIResponse(text)
            const aiMsg = {
                role: 'assistant',
                content: aiText,
                timestamp: new Date().toISOString(),
            }

            setConversations((prev) =>
                prev.map((c) =>
                    c.id === convId ? { ...c, messages: [...c.messages, aiMsg] } : c
                )
            )
        } catch {
            const errorMsg = {
                role: 'assistant',
                content: 'Sorry, I encountered an error processing your request. Please try again.',
                timestamp: new Date().toISOString(),
            }
            setConversations((prev) =>
                prev.map((c) =>
                    c.id === convId ? { ...c, messages: [...c.messages, errorMsg] } : c
                )
            )
        } finally {
            setIsLoading(false)
        }
    }, [activeConversationId, createConversation])

    const handleNewChat = useCallback(() => {
        setActiveConversationId(null)
        setSidebarOpen(false)
    }, [])

    const handleSelectChat = useCallback((id) => {
        setActiveConversationId(id)
        setSidebarOpen(false)
    }, [])

    const handleDeleteChat = useCallback((id) => {
        setConversations((prev) => prev.filter((c) => c.id !== id))
        if (activeConversationId === id) {
            setActiveConversationId(null)
        }
    }, [activeConversationId])

    return (
        <div className="chat-layout">
            <Sidebar
                conversations={conversations}
                activeId={activeConversationId}
                onNewChat={handleNewChat}
                onSelectChat={handleSelectChat}
                onDeleteChat={handleDeleteChat}
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
                user={user}
                onShowAuth={() => handleShowAuth('login')}
                onLogout={handleLogout}
            />
            <ChatWindow
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
                onShowAuth={handleShowAuth}
                user={user}
                onLogout={handleLogout}
            />
            {showAuthModal && (
                <AuthModal
                    onClose={() => setShowAuthModal(false)}
                    onLogin={(userData) => setUser(userData)}
                    initialMode={authMode}
                />
            )}
        </div>
    )
}

export default ChatPage
