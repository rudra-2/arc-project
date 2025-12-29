// Use configuration from config.js (loaded before this script in popup.html)

if (!window.EXTENSION_CONFIG) {
  window.EXTENSION_CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    API_ENDPOINTS: {
      login: '/api/login/',
      register: '/api/register/',
      portfolio: '/api/portfolio/',
      wallet: '/api/wallet/',
      transfer: '/api/transfer/',
      merchant: '/api/merchant/',
      face_auth: '/api/face-auth/',
      market_data: '/api/market-data/',
      transactions: '/api/transactions/'
    }
  };
}

console.log('Extension Config:', window.EXTENSION_CONFIG);
console.log('API Base URL:', window.EXTENSION_CONFIG.API_BASE_URL);

document.addEventListener('DOMContentLoaded', async () => {
  console.log('DOM Content Loaded');
  

  chrome.runtime.sendMessage({ type: 'CLEAR_PAYMENT_BADGE' });
  
  // Check if elements exist
  console.log('Elements found:', {
    loginBtn: !!document.getElementById('loginBtn'),
    usernameField: !!document.getElementById('username'),
    passwordField: !!document.getElementById('password'),
    loginSection: !!document.getElementById('login-section'),
    walletSection: !!document.getElementById('wallet-section')
  });
  
  
  window.addEventListener('beforeunload', async () => {
    if (window.paymentInProgress || window.paymentInitiated) {
      console.log('Extension closing during payment process - cancelling...');
      
      // If we have a transaction hash, cancel it on the backend
      if (window.currentTransactionHash) {
        try {
          const token = await getToken();
          if (token) {
            await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/transactions/cancel/`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({ tx_hash: window.currentTransactionHash })
            });
          }
        } catch (error) {
          console.error('Error cancelling transaction:', error);
        }
      }
      
      // Always notify Curve of cancellation
      chrome.runtime.sendMessage({ 
        type: 'ARC_PAYMENT_STATUS', 
        payload: { 
          status: 'cancelled',
          reason: 'Extension closed during payment process'
        } 
      });
    }
  });
  
  // Also handle when popup is closed via ESC or clicking outside
  window.addEventListener('unload', async () => {
    if (window.paymentInProgress || window.paymentInitiated) {
      console.log('Extension popup closed during payment process - cancelling...');
      
      // If we have a transaction hash, cancel it on the backend
      if (window.currentTransactionHash) {
        try {
          const token = await getToken();
          if (token) {
            await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/transactions/cancel/`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({ tx_hash: window.currentTransactionHash })
            });
          }
        } catch (error) {
          console.error('Error cancelling transaction:', error);
        }
      }
      
      // Always notify Curve of cancellation
      chrome.runtime.sendMessage({ 
        type: 'ARC_PAYMENT_STATUS', 
        payload: { 
          status: 'cancelled',
          reason: 'Extension popup closed'
        } 
      });
    }
  });
  
  // Elements
  const addressEl = document.getElementById('address');
  const balanceEl = document.getElementById('balance');
  const loginBtn = document.getElementById('loginBtn');
  const registerBtn = document.getElementById('registerBtn');
  const logoutBtn = document.getElementById('logoutBtn');
  const toggleAuthMode = document.getElementById('toggleAuthMode');
  const loginSection = document.getElementById('login-section');
  const walletSection = document.getElementById('wallet-section');
  const paymentSection = document.getElementById('payment-section');
  const paymentAmountEl = document.getElementById('payment-amount');
  const faceAuthBtn = document.getElementById('faceAuthBtn');
  const cancelPaymentBtn = document.getElementById('cancelPaymentBtn');
  const paymentStatus = document.getElementById('paymentStatus');
  const showManualTransfer = document.getElementById('showManualTransfer');
  const manualSection = document.getElementById('manual-section');
  const manualToAddress = document.getElementById('manualToAddress');
  const manualAmount = document.getElementById('manualAmount');
  const manualSendBtn = document.getElementById('manualSendBtn');
  const manualReceiveAddress = document.getElementById('manualReceiveAddress');
  const manualBackBtn = document.getElementById('manualBackBtn');
  const manualStatus = document.getElementById('manualStatus');
  const showMerchantWallet = document.getElementById('showMerchantWallet');
  const merchantSection = document.getElementById('merchant-section');
  const merchantName = document.getElementById('merchantName');
  const merchantFetchBtn = document.getElementById('merchantFetchBtn');
  const merchantWalletInfo = document.getElementById('merchantWalletInfo');
  const merchantBackBtn = document.getElementById('merchantBackBtn');

  // Auth mode toggle
  let isRegisterMode = false;
  function setAuthMode(registerMode) {
    isRegisterMode = registerMode;
    document.getElementById('email').style.display = registerMode ? '' : 'none';
    registerBtn.style.display = registerMode ? '' : 'none';
    loginBtn.style.display = registerMode ? 'none' : '';
    toggleAuthMode.innerText = registerMode ? 'Already have an account? Login' : "Don't have an account? Register";
    document.getElementById('loginError').innerText = '';
  }
  if (toggleAuthMode) toggleAuthMode.onclick = (e) => {
    e.preventDefault();
    setAuthMode(!isRegisterMode);
  };
  setAuthMode(false);

  // Token helpers
  async function getToken() {
    return new Promise(resolve => {
      chrome.storage.local.get(['token'], result => resolve(result.token));
    });
  }
  async function setToken(token) {
    return new Promise(resolve => {
      chrome.storage.local.set({ token }, resolve);
    });
  }
  async function clearToken() {
    return new Promise(resolve => {
      chrome.storage.local.remove('token', resolve);
    });
  }

  // API helpers
  async function fetchPortfolio(token) {
    try {
      console.log('Fetching portfolio with token:', token);
      const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/portfolio/`, {
        method: 'GET',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Portfolio fetch response status:', res.status);
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      
      const data = await res.json();
      console.log('Portfolio API response:', data);
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      return data.portfolio;
    } catch (error) {
      console.error('fetchPortfolio error:', error);
      return { 
        wallets: [],
        total_value_usd: 0,
        error: error.message
      };
    }
  }

  async function fetchWallet(token) {
    try {
      const portfolio = await fetchPortfolio(token);
      if (portfolio.error) {
        throw new Error(portfolio.error);
      }
      
      // Find ARC wallet from portfolio
      const arcWallet = portfolio.wallets.find(w => w.symbol === 'ARC');
      if (!arcWallet) {
        throw new Error('ARC wallet not found');
      }
      
      return {
        public_key: arcWallet.public_key,
        balance: arcWallet.balance,
        value_usd: arcWallet.value_usd,
        network: arcWallet.network || 'mainnet',
        symbol: arcWallet.symbol,
        name: arcWallet.name
      };
    } catch (error) {
      console.error('fetchWallet error:', error);
      return { 
        public_key: 'Error: ' + error.message, 
        balance: 'Error loading',
        network: 'Error'
      };
    }
  }
  async function fetchCryptos() {
    try {
      const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/market-data/`);
      const data = await res.json();
      console.log('Market data API response:', data);
      return data.market_data || [];
    } catch (error) {
      console.error('fetchCryptos error:', error);
      return [];
    }
  }
  async function login(username, password) {
    try {
      console.log('Attempting login with:', { username, api_url: `${EXTENSION_CONFIG.API_BASE_URL}/api/login/` });
      
      const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      console.log('Login response status:', res.status);
      const data = await res.json();
      console.log('Login response data:', data);
      
      if (data.token) {
        await setToken(data.token);
        return data.token;
      } else {
        throw new Error(data.error || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }
  async function register(username, email, password) {
    try {
      const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
      });
      const data = await res.json();
      console.log('Register response:', data); // Debug log
      
      if (data.token) {
        await setToken(data.token);
        return data.token;
      } else {
        throw new Error(data.error || 'Registration failed');
      }
    } catch (error) {
      console.error('Register error:', error);
      throw error;
    }
  }
  async function logout(token) {
    await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/logout/`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    await clearToken();
  }
  async function faceAuth(token, imageData) {
    console.log('faceAuth called with token:', token); // Debug log
    const formData = new FormData();
    formData.append('image', imageData);
    console.log('Sending face auth request to:', `${EXTENSION_CONFIG.API_BASE_URL}/api/face-auth/`); // Debug log
    console.log('Authorization header:', `Bearer ${token}`); // Debug log
    
    const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/face-auth/`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });
    
    console.log('Face auth response status:', res.status); // Debug log
    const responseData = await res.json();
    console.log('Face auth response data:', responseData); // Debug log
    
    return responseData.face_ok;
  }
  async function createTransaction(token, toAddress, amount, transactionType = 'transfer') {
    const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/transactions/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        to_address: toAddress, 
        amount: amount,
        crypto_symbol: 'ARC',
        transaction_type: transactionType,
        memo: `Extension payment to ${toAddress}`
      })
    });
    return await res.json();
  }
  async function manualTransfer(token, toAddress, amount) {
    // Use createTransaction for wallet-to-wallet transfers
    const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/transactions/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        to_address: toAddress, 
        amount: parseFloat(amount),
        crypto_symbol: 'ARC',
        transaction_type: 'transfer',
        memo: `Manual transfer to ${toAddress}`
      })
    });
    const result = await res.json();
    console.log('Manual transfer result:', result);
    return result;
  }
  
  async function processMerchantPayment(token, merchantName, amount, cryptoSymbol = 'ARC') {
    const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/merchant/payment/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        merchant_name: merchantName, 
        amount: amount,
        crypto_symbol: cryptoSymbol,
        memo: `Extension payment to ${merchantName}`
      })
    });
    return await res.json();
  }
  
  async function fetchMerchantInfo(merchantName) {
    const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/merchant/info/?merchant_name=${merchantName}`);
    return await res.json();
  }
  
  async function fetchMerchantWallet(merchantName) {
    const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/merchant/${merchantName}/`);
    return await res.json();
  }
  
  async function fetchTransactionHistory(token) {
    try {
      const res = await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/transactions/`, {
        method: 'GET',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      
      const data = await res.json();
      return data.transactions || [];
    } catch (error) {
      console.error('fetchTransactionHistory error:', error);
      return [];
    }
  }

  // Section helpers
  function showSection(sectionId) {
    loginSection.style.display = 'none';
    walletSection.style.display = 'none';
    paymentSection.style.display = 'none';
    manualSection.style.display = 'none';
    merchantSection.style.display = 'none';
    document.getElementById(sectionId).style.display = 'block';
  }

  // Payment trigger from Curve
  let curveAmount = null;
  chrome.storage.local.get('arc_order_amount', (data) => {
    console.log('Storage data:', data); // Debug log
    if (data.arc_order_amount) {
      curveAmount = parseFloat(data.arc_order_amount);
      console.log('Curve amount:', curveAmount); // Debug log
      
      // Set payment initiated flag - payment process has started
      window.paymentInitiated = true;
      window.paymentInProgress = false;
      window.currentTransactionHash = null;
      
      // Create payment amount display if it doesn't exist
      let paymentAmountEl = document.getElementById('payment-amount');
      if (!paymentAmountEl) {
        paymentAmountEl = document.createElement('p');
        paymentAmountEl.id = 'payment-amount';
        const paymentSection = document.getElementById('payment-section');
        if (paymentSection) {
          paymentSection.insertBefore(paymentAmountEl, paymentSection.firstChild);
        }
      }
      
      if (paymentAmountEl) {
        paymentAmountEl.innerText = `Order Amount: ${curveAmount} ARC`;
        paymentAmountEl.style.fontSize = '18px';
        paymentAmountEl.style.fontWeight = 'bold';
        paymentAmountEl.style.color = '#fff';
        paymentAmountEl.style.textAlign = 'center';
        paymentAmountEl.style.marginBottom = '20px';
      }
      
      showSection('payment-section');
      // Clear the storage after use
      chrome.storage.local.remove('arc_order_amount');
      
      // Start camera
      const video = document.getElementById('video');
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true }).then((stream) => {
          video.srcObject = stream;
        }).catch((err) => {
          console.error('Camera access error:', err);
          paymentStatus.innerText = 'Camera access denied. Please enable camera.';
        });
      }
      
      faceAuthBtn.onclick = async () => {
        paymentStatus.innerText = 'Authenticating...';
        
        // Get token first and validate
        const token = await getToken();
        if (!token) {
          paymentStatus.innerText = 'Please login first.';
          showSection('login-section');
          return;
        }
        
        console.log('Face auth token:', token); // Debug log
        
        // Show current wallet info during face auth
        const wallet = await fetchWallet(token);
        if (wallet) {
          paymentStatus.innerText = `Wallet: ${wallet.public_key?.substring(0, 20)}...\nBalance: ${wallet.balance} ARC\nAuthenticating...`;
        }
        
        // Capture frame
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        canvas.toBlob(async (blob) => {
          try {
            console.log('Sending face auth request with token:', token); // Debug log
            const faceOk = await faceAuth(token, blob);
            if (!faceOk) {
              paymentStatus.innerText = 'Face authentication failed.';
              chrome.runtime.sendMessage({ type: 'ARC_PAYMENT_STATUS', payload: { status: 'failed' } });
              return;
            }
            
            paymentStatus.innerText = 'Processing payment...';
            
            // Set a flag to track payment in progress
            window.paymentInProgress = true;
            window.currentTransactionHash = null;
            
            // Process merchant payment
            const result = await processMerchantPayment(token, 'curve-merchant-1', curveAmount, 'ARC');
            if (result.transaction_hash) {
              // Store transaction hash for potential cancellation
              window.currentTransactionHash = result.transaction_hash;
              
              // Payment completed successfully
              window.paymentInProgress = false;
              window.paymentInitiated = false; // Clear the initiated flag
              
              // Show initial success message
              paymentStatus.innerText = `✅ Payment Successful!\nAmount: ${curveAmount} ARC\nTo: Curve Merchant\nTx: ${result.transaction_hash.substring(0, 10)}...`;
              
              // Update wallet balance immediately
              const updatedWallet = await fetchWallet(token);
              if (updatedWallet) {
                balanceEl.innerText = 'Balance: ' + updatedWallet.balance;
              }
              
              // Send success message to Curve with delay to ensure it's received
              console.log('Sending success message to Curve...');
              chrome.runtime.sendMessage({ 
                type: 'ARC_PAYMENT_STATUS', 
                payload: { 
                  status: 'success',
                  amount: curveAmount,
                  transactionId: result.transaction_hash,
                  currency: 'ARC'
                } 
              }, (response) => {
                console.log('Success message sent to Curve:', response);
              });
              
              // Wait a bit to ensure message is processed
              setTimeout(() => {
                // Countdown timer for auto-close
                let countdown = 5; // Increased from 3 to 5 seconds
                const countdownInterval = setInterval(() => {
                  paymentStatus.innerText = `✅ Payment Successful!\nAmount: ${curveAmount} ARC\nTo: Curve Merchant\n\nClosing in ${countdown} seconds...`;
                  countdown--;
                  
                  if (countdown < 0) {
                    clearInterval(countdownInterval);
                    console.log('Sending CLOSE_EXTENSION_TAB message...');
                    chrome.runtime.sendMessage({ type: 'CLOSE_EXTENSION_TAB' }, (response) => {
                      console.log('Close response:', response);
                      if (chrome.runtime.lastError) {
                        console.error('Close error:', chrome.runtime.lastError);
                        // Fallback: try to close window
                        window.close();
                      }
                    });
                  }
                }, 1000);
              }, 1000); // Wait 1 second before starting countdown
              
            } else {
              // Payment failed
              window.paymentInProgress = false;
              window.paymentInitiated = false; // Clear the initiated flag
              window.currentTransactionHash = null;
              paymentStatus.innerText = 'Payment failed: ' + (result.error || 'Unknown error');
              chrome.runtime.sendMessage({ type: 'ARC_PAYMENT_STATUS', payload: { status: 'failed' } });
            }
          } catch (error) {
            // Payment failed with error
            window.paymentInProgress = false;
            window.paymentInitiated = false; // Clear the initiated flag
            window.currentTransactionHash = null;
            console.error('Payment error:', error);
            paymentStatus.innerText = 'Payment failed: ' + error.message;
            chrome.runtime.sendMessage({ type: 'ARC_PAYMENT_STATUS', payload: { status: 'failed' } });
          }
        }, 'image/jpeg');
      };
      return;
    }
    // If not from Curve, show login/wallet as usual
    initWalletFlow();
  });

  // Read query params for direct payment open
  const params = new URLSearchParams(location.search);
  const qpAmount = params.get('amount');
  if (qpAmount && paymentAmountEl) {
    paymentAmountEl.innerText = qpAmount;
    paymentSection?.classList.remove('hidden');
  }

  async function initWalletFlow() {
    let token = await getToken();
    if (token) {
      try {
        showSection('wallet-section');
        console.log('Token found:', token); // Debug log
        const wallet = await fetchWallet(token);
        console.log('Wallet data:', wallet); // Debug log
        
        if (wallet) {
          addressEl.innerText = 'Wallet: ' + (wallet.public_key || 'Not available');
          balanceEl.innerText = 'Balance: ' + (wallet.balance !== undefined ? wallet.balance : 'Not available');
        } else {
          addressEl.innerText = 'Wallet: Error loading';
          balanceEl.innerText = 'Balance: Error loading';
        }
        
        const cryptos = await fetchCryptos();
        const cryptoList = document.getElementById('crypto-list');
        if (cryptoList) {
          cryptoList.innerHTML = cryptos.map(crypto => 
            `<div class="crypto-item">
              <span class="crypto-symbol">${crypto.base_symbol}</span>
              <span class="crypto-price">$${crypto.current_price?.toFixed(6) || '0.00'}</span>
              <span class="crypto-change ${crypto.price_change_24h >= 0 ? 'positive' : 'negative'}">
                ${crypto.price_change_24h >= 0 ? '+' : ''}${crypto.price_change_24h?.toFixed(2) || '0.00'}%
              </span>
            </div>`
          ).join('');
        }
        
        // Load transaction history
        const transactions = await fetchTransactionHistory(token);
        const transactionHistory = document.getElementById('transaction-history');
        if (transactionHistory) {
          if (transactions.length > 0) {
            transactionHistory.innerHTML = transactions.slice(0, 5).map(tx => 
              `<div class="transaction-item">
                <div class="transaction-header">
                  <span class="transaction-type">${tx.transaction_type || 'Transfer'}</span>
                  <span class="transaction-amount">${tx.amount > 0 ? '+' : ''}${tx.amount} ${tx.crypto_symbol || 'ARC'}</span>
                </div>
                <div class="transaction-details">
                  <div>To: ${tx.to_address ? tx.to_address.substring(0, 20) + '...' : 'N/A'}</div>
                  <div class="transaction-hash">Tx: ${tx.transaction_hash ? tx.transaction_hash.substring(0, 16) + '...' : 'Pending'}</div>
                  <div>Status: ${tx.status || 'pending'}</div>
                </div>
              </div>`
            ).join('');
          } else {
            transactionHistory.innerHTML = '<p class="loading-text">No transactions yet</p>';
          }
        }
        
        if (manualReceiveAddress) {
          manualReceiveAddress.innerText = wallet.public_key || 'Not available';
        }
      } catch (error) {
        console.error('initWalletFlow error:', error);
        addressEl.innerText = 'Wallet: Error - ' + error.message;
        balanceEl.innerText = 'Balance: Error loading';
      }
    } else {
      showSection('login-section');
    }
  }

  if (loginBtn) loginBtn.onclick = async () => {
    console.log('Login button clicked');
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    console.log('Login credentials:', { username: username ? 'provided' : 'empty', password: password ? 'provided' : 'empty' });
    
    if (!username || !password) {
      document.getElementById('loginError').innerText = 'Please enter both username and password';
      return;
    }
    
    try {
      console.log('Calling login function...');
      await login(username, password);
      console.log('Login successful, initializing wallet...');
      await initWalletFlow();
    } catch (e) {
      console.error('Login failed:', e);
      document.getElementById('loginError').innerText = e.message || 'Login failed';
    }
  };
  if (registerBtn) registerBtn.onclick = async () => {
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    try {
      await register(username, email, password);
      await initWalletFlow();
    } catch (e) {
      document.getElementById('loginError').innerText = e.message || 'Register failed';
    }
  };
  if (logoutBtn) logoutBtn.onclick = async () => {
    const token = await getToken();
    await logout(token);
    showSection('login-section');
  };
  if (showManualTransfer) showManualTransfer.onclick = () => {
    showSection('manual-section');
  };
  if (manualBackBtn) manualBackBtn.onclick = () => {
    showSection('wallet-section');
  };
  if (manualSendBtn) manualSendBtn.onclick = async () => {
    const token = await getToken();
    const toAddress = manualToAddress.value;
    const amount = manualAmount.value;
    
    // Validate inputs
    if (!toAddress || !amount) {
      manualStatus.innerText = 'Please enter both address and amount.';
      return;
    }
    
    if (parseFloat(amount) <= 0) {
      manualStatus.innerText = 'Amount must be greater than 0.';
      return;
    }
    
    manualStatus.innerText = 'Processing transfer...';
    
    try {
      const result = await manualTransfer(token, toAddress, amount);
      
      if (result.transaction_hash) {
        manualStatus.innerText = `✅ Transfer successful!\nTx Hash: ${result.transaction_hash.substring(0, 20)}...\nAmount: ${amount} ARC`;
        
        // Clear form
        manualToAddress.value = '';
        manualAmount.value = '';
        
        // Update wallet balance
        const updatedWallet = await fetchWallet(token);
        if (updatedWallet && balanceEl) {
          balanceEl.innerText = 'Balance: ' + updatedWallet.balance;
        }
        
        // Refresh transaction history
        const transactions = await fetchTransactionHistory(token);
        const transactionHistory = document.getElementById('transaction-history');
        if (transactionHistory) {
          if (transactions.length > 0) {
            transactionHistory.innerHTML = transactions.slice(0, 5).map(tx => 
              `<div class="transaction-item">
                <div class="transaction-header">
                  <span class="transaction-type">${tx.transaction_type || 'Transfer'}</span>
                  <span class="transaction-amount">${tx.amount > 0 ? '+' : ''}${tx.amount} ${tx.crypto_symbol || 'ARC'}</span>
                </div>
                <div class="transaction-details">
                  <div>To: ${tx.to_address ? tx.to_address.substring(0, 20) + '...' : 'N/A'}</div>
                  <div class="transaction-hash">Tx: ${tx.transaction_hash ? tx.transaction_hash.substring(0, 16) + '...' : 'Pending'}</div>
                  <div>Status: ${tx.status || 'pending'}</div>
                </div>
              </div>`
            ).join('');
          } else {
            transactionHistory.innerHTML = '<p class="loading-text">No transactions yet</p>';
          }
        }
      } else {
        manualStatus.innerText = 'Transfer failed: ' + (result.error || result.message || 'Unknown error');
      }
    } catch (error) {
      console.error('Manual transfer error:', error);
      manualStatus.innerText = 'Transfer failed: ' + error.message;
    }
  };
  if (showMerchantWallet) showMerchantWallet.onclick = () => {
    showSection('merchant-section');
  };
  if (merchantBackBtn) merchantBackBtn.onclick = () => {
    showSection('wallet-section');
  };
  if (merchantFetchBtn) merchantFetchBtn.onclick = async () => {
    const name = merchantName.value;
    merchantWalletInfo.innerText = 'Loading...';
    const result = await fetchMerchantWallet(name);
    if (result.merchant_wallet) {
      merchantWalletInfo.innerText = `Name: ${result.merchant_wallet.merchant_name}\nAddress: ${result.merchant_wallet.public_key}\nBalance: ${result.merchant_wallet.balance}`;
    } else {
      merchantWalletInfo.innerText = result.error || 'Not found.';
    }
  };
  
  // Cancel payment button handler
  if (cancelPaymentBtn) cancelPaymentBtn.onclick = async () => {
    console.log('Cancel payment button clicked');
    
    // If transaction is in progress, cancel it
    if (window.currentTransactionHash) {
      try {
        const token = await getToken();
        if (token) {
          await fetch(`${EXTENSION_CONFIG.API_BASE_URL}/api/transactions/cancel/`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ tx_hash: window.currentTransactionHash })
          });
        }
      } catch (error) {
        console.error('Error cancelling transaction:', error);
      }
    }
    
    // Reset payment flags
    window.paymentInProgress = false;
    window.paymentInitiated = false;
    window.currentTransactionHash = null;
    
    // Notify Curve of cancellation
    chrome.runtime.sendMessage({ 
      type: 'ARC_PAYMENT_STATUS', 
      payload: { 
        status: 'cancelled',
        reason: 'User cancelled payment manually'
      } 
    });
    
    // Update UI
    paymentStatus.innerText = 'Payment cancelled by user';
    
    // Close extension after a short delay
    setTimeout(() => {
      chrome.runtime.sendMessage({ type: 'CLOSE_EXTENSION_TAB' });
    }, 1500);
  };
});
