import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { HiOutlineArrowLeft } from 'react-icons/hi2'
import './AuthPage.css'

function AuthPage() {
    const [isLogin, setIsLogin] = useState(true)
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [name, setName] = useState('')
    const navigate = useNavigate()

    const handleSubmit = (e) => {
        e.preventDefault()
        // TODO: Connect to Django backend auth API
        console.log(isLogin ? 'Login' : 'Register', { email, password, name })
    }

    return (
        <div className="auth">
            <div className="auth__card">
                {/* Logo */}
                <div className="auth__logo">
                    <div className="auth__logo-icon">Rx</div>
                    <div className="auth__logo-text">
                        Rx<span>Chat</span>
                    </div>
                </div>

                <h1 className="auth__title">
                    {isLogin ? 'Welcome back' : 'Create an account'}
                </h1>
                <p className="auth__subtitle">
                    {isLogin
                        ? 'Sign in to access your chat history'
                        : 'Register to save your conversations'}
                </p>

                {/* Form */}
                <form className="auth__form" onSubmit={handleSubmit}>
                    {!isLogin && (
                        <div className="auth__field">
                            <label className="auth__label" htmlFor="name">Full Name</label>
                            <input
                                id="name"
                                className="auth__input"
                                type="text"
                                placeholder="Enter your name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required
                            />
                        </div>
                    )}

                    <div className="auth__field">
                        <label className="auth__label" htmlFor="email">Email</label>
                        <input
                            id="email"
                            className="auth__input"
                            type="email"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div className="auth__field">
                        <label className="auth__label" htmlFor="password">Password</label>
                        <input
                            id="password"
                            className="auth__input"
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            minLength={8}
                        />
                    </div>

                    <button type="submit" className="auth__submit">
                        {isLogin ? 'Sign In' : 'Create Account'}
                    </button>

                    <div className="auth__divider">or</div>

                    <button type="button" className="auth__google">
                        <svg width="18" height="18" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                        </svg>
                        Continue with Google
                    </button>
                </form>

                {/* Toggle login/register */}
                <div className="auth__toggle">
                    {isLogin ? "Don't have an account? " : 'Already have an account? '}
                    <button type="button" onClick={() => setIsLogin(!isLogin)}>
                        {isLogin ? 'Register' : 'Sign In'}
                    </button>
                </div>

                {/* Back to chat */}
                <button className="auth__back" onClick={() => navigate('/')}>
                    <HiOutlineArrowLeft size={14} />
                    Continue without signing in
                </button>
            </div>
        </div>
    )
}

export default AuthPage
