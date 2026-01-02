import { useState } from "react"
import axios from "axios"
import { useNavigate } from "react-router-dom"

const Login = () => {
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: "", password: "" })
  const [isLoading, setIsLoading] = useState(false)

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'}/login/`, form)
      localStorage.setItem("token", res.data.token)
      localStorage.setItem("user", JSON.stringify(res.data.user))
      navigate("/dashboard")
    } catch (error) {
      alert("Login failed: " + (error.response?.data?.error || "Try again"))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full min-h-screen relative overflow-hidden cyber-grid">
      {/* Animated Background Orbs */}
      <div className="absolute inset-0">
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-3/4 right-1/4 w-96 h-96 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute bottom-1/4 left-1/2 w-80 h-80 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Main Container - Scrollable */}
      <div className="relative z-10 w-full min-h-screen flex items-center justify-center p-4 py-8 overflow-y-auto">
        <div className="w-full max-w-md my-auto">
          
          {/* Header Section */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-24 h-24 rounded-full glass-intense neon-cyan mb-4 hover-scale shadow-xl border-2 border-cyan-400/30 p-2">
              <div className="w-20 h-20 rounded-full overflow-hidden bg-white/10 flex items-center justify-center">
                <img 
                  src="/arc.png" 
                  alt="ARC Logo" 
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
            <h1 className="text-3xl font-bold text-gradient-cyan mb-2">ARC EXCHANGE</h1>
            <p className="text-gray-400 text-base">Next-Gen Crypto Trading Platform</p>
            
            {/* Crypto Price Ticker */}
            <div className="flex justify-center space-x-4 mt-3 text-xs">
              <div className="flex items-center space-x-1">
                <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-gray-300">BTC</span>
                <span className="text-green-400 font-mono">$67,234</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse"></div>
                <span className="text-gray-300">ETH</span>
                <span className="text-blue-400 font-mono">$3,456</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-pulse"></div>
                <span className="text-gray-300">SOL</span>
                <span className="text-purple-400 font-mono">$156</span>
              </div>
            </div>
          </div>

          {/* Demo Credentials Info */}
          <div className="mb-4 glass rounded-xl p-4 border border-cyan-400/30 hover-glow transition-all duration-300 group">
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
              <p className="text-xs font-semibold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">Demo Account</p>
            </div>
            <div className="space-y-2 text-xs text-gray-300 font-mono">
              <div className="flex items-center space-x-2 group-hover:text-cyan-300 transition-colors">
                <span className="text-gray-500">→</span>
                <span>Username:</span>
                <span className="text-cyan-400 font-semibold">investor1</span>
              </div>
              <div className="flex items-center space-x-2 group-hover:text-cyan-300 transition-colors">
                <span className="text-gray-500">→</span>
                <span>Password:</span>
                <span className="text-cyan-400 font-semibold">password123</span>
              </div>
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="glass-intense rounded-2xl p-6 space-y-5 hover-glow">
            <div className="text-center mb-5">
              <h2 className="text-xl font-bold text-white mb-1">Welcome Back</h2>
              <p className="text-gray-400 text-sm">Access your crypto portfolio</p>
            </div>

            {/* Username Field */}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
                </svg>
              </div>
              <input
                className="w-full pl-9 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-400 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/50 focus:outline-none transition-all duration-300 font-mono text-sm"
                name="username"
                placeholder="Username or Email"
                value={form.username}
                onChange={handleChange}
                required
              />
            </div>

            {/* Password Field */}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd"/>
                </svg>
              </div>
              <input
                className="w-full pl-9 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-400 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/50 focus:outline-none transition-all duration-300 font-mono text-sm"
                name="password"
                placeholder="Password"
                type="password"
                value={form.password}
                onChange={handleChange}
                required
              />
            </div>

            {/* Security Features */}
            <div className="flex items-center justify-between text-xs">
              <label className="flex items-center text-gray-300 cursor-pointer">
                <input type="checkbox" className="mr-2 rounded bg-white/5 border-white/10 text-cyan-400 focus:ring-cyan-400/50"/>
                Remember me
              </label>
              <button type="button" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                Forgot password?
              </button>
            </div>

            {/* Login Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 rounded-xl text-white font-semibold transition-all duration-300 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-cyan-500/25"
            >
              {isLoading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span className="text-sm">Authenticating...</span>
                </div>
              ) : (
                "Access Portfolio"
              )}
            </button>

            {/* Biometric Auth */}
            <div className="flex space-x-2">
              <button
                type="button"
                className="flex-1 py-2.5 glass border border-white/10 rounded-xl text-gray-300 hover:border-purple-400 hover:text-purple-400 transition-all duration-300 flex items-center justify-center space-x-1.5 text-sm"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 1L3 5V11C3 16.55 6.84 21.74 12 23C17.16 21.74 21 16.55 21 11V5L12 1M12 7C13.4 7 14.8 8.6 14.8 10V11.5C15.4 12.1 16 12.8 16 14C16 15.7 14.7 17 13 17H11C9.3 17 8 15.7 8 14C8 12.8 8.6 12.1 9.2 11.5V10C9.2 8.6 10.6 7 12 7M12 8.2C11.2 8.2 10.5 8.9 10.5 10V11.5H13.5V10C13.5 8.9 12.8 8.2 12 8.2Z"/>
                </svg>
                <span>Face ID</span>
              </button>
              <button
                type="button"
                className="flex-1 py-2.5 glass border border-white/10 rounded-xl text-gray-300 hover:border-gold-400 hover:text-yellow-400 transition-all duration-300 flex items-center justify-center space-x-1.5 text-sm"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.81 4.47C17.73 4.47 17.65 4.45 17.58 4.41C17.5 4.38 17.42 4.34 17.36 4.27C17.29 4.21 17.24 4.14 17.2 4.06C17.16 3.99 17.14 3.91 17.14 3.83C17.14 3.75 17.16 3.67 17.2 3.6C17.24 3.52 17.29 3.45 17.36 3.39C17.42 3.32 17.5 3.28 17.58 3.25C17.65 3.21 17.73 3.19 17.81 3.19C17.89 3.19 17.97 3.21 18.04 3.25C18.12 3.28 18.2 3.32 18.26 3.39C18.33 3.45 18.38 3.52 18.42 3.6C18.46 3.67 18.48 3.75 18.48 3.83C18.48 3.91 18.46 3.99 18.42 4.06C18.38 4.14 18.33 4.21 18.26 4.27C18.2 4.34 18.12 4.38 18.04 4.41C17.97 4.45 17.89 4.47 17.81 4.47M12 2A10 10 0 0 0 2 12A10 10 0 0 0 12 22A10 10 0 0 0 22 12A10 10 0 0 0 12 2M12 4A8 8 0 0 1 20 12A8 8 0 0 1 12 20A8 8 0 0 1 4 12A8 8 0 0 1 12 4Z"/>
                </svg>
                <span>Touch ID</span>
              </button>
            </div>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-3 bg-transparent text-gray-400">New to crypto?</span>
              </div>
            </div>

            {/* Register Link */}
            <button
              type="button"
              onClick={() => navigate("/register")}
              className="w-full py-2.5 border border-white/20 rounded-xl text-white hover:bg-white/5 transition-all duration-300 font-medium text-sm"
            >
              Create Account
            </button>
          </form>

          {/* Footer */}
          <div className="text-center mt-6 text-gray-400 text-xs">
            <p>Secured by military-grade encryption</p>
            <div className="flex justify-center space-x-3 mt-2">
              <span className="flex items-center space-x-1">
                <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>
                <span>256-bit SSL</span>
              </span>
              <span className="flex items-center space-x-1">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full"></div>
                <span>2FA Enabled</span>
              </span>
              <span className="flex items-center space-x-1">
                <div className="w-1.5 h-1.5 bg-purple-400 rounded-full"></div>
                <span>Cold Storage</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login
