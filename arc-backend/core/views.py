from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer, PortfolioSerializer, TradingPairSerializer, OrderSerializer, TradeSerializer, TransactionSerializer
from .models import User, Token, Portfolio, CryptoWallet, TradingPair, Order, Trade, Transaction, MerchantWallet, FaceData, PriceHistory, CurveCart
from .utils import generate_wallet, generate_transaction_hash, generate_order_id, generate_trade_id, initialize_trading_pairs, simulate_all_prices, calculate_portfolio_value, process_crypto_transfer, execute_market_order, get_crypto_name
import hashlib
import secrets
import json
import face_recognition
import numpy as np
from datetime import datetime, timedelta
import random
import uuid

# Constants
SYMBOLS = ['BTC', 'ETH', 'ARC', 'SOL', 'USDT', 'BNB', 'ADA', 'DOT', 'LINK', 'LTC']

# Simple token authentication using database
class SimpleTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        print(f"Auth header: {auth_header}")  # Debug
        
        if not auth_header:
            return None
            
        try:
            token_type, token = auth_header.split(' ', 1)
            # Accept both 'Token' and 'Bearer' authentication types
            if token_type.lower() not in ['token', 'bearer']:
                return None
        except ValueError:
            return None
        
        print(f"Looking for token: {token}")  # Debug
        
        # Look up token in database
        try:
            token_obj = Token.objects(token=token).first()
            if token_obj and token_obj.user:
                print(f"Found user: {token_obj.user.username}")  # Debug
                return (token_obj.user, token)  # Return (user, auth) tuple
            else:
                print("Token not found in database")  # Debug
        except Exception as e:
            print(f"Error finding token: {e}")
        
        print("No matching token found")  # Debug
        return None

    def authenticate_header(self, request):
        return 'Token'

# Authentication views
@api_view(['POST'])
def register(request):
    try:
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        
        # Check if user already exists
        if User.objects(username=username).first() or User.objects(email=email).first():
            return Response({'error': 'Username or email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Hash password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        user = User(username=username, email=email, password=hashed_password)
        user.save()
        
        # Process face image if provided
        if 'image' in request.FILES:
            try:
                image_file = request.FILES['image']
                image = face_recognition.load_image_file(image_file)
                face_encodings = face_recognition.face_encodings(image)
                
                if face_encodings:
                    face_encoding = face_encodings[0]
                    face_data = FaceData(user=user, encoding=face_encoding.tobytes())
                    face_data.save()
            except Exception as e:
                print(f"Face processing error: {e}")
                
        portfolio = Portfolio(user=user)
        
        # Create default crypto wallets
        default_cryptos = ['BTC', 'ETH', 'ARC', 'USDT', 'SOL']
        for crypto in default_cryptos:
            public_key, private_key = generate_wallet()
            wallet = CryptoWallet(
                symbol=crypto,
                name=get_crypto_name(crypto),
                public_key=public_key,
                private_key=json.dumps(private_key),
                balance=1000.0 if crypto == 'USDT' else 0.1  # Start with some demo balance
            )
            portfolio.wallets.append(wallet)
        
        portfolio.save()
        
        # Create authentication token
        token_value = secrets.token_hex(32)
        token = Token(user=user, token=token_value)
        token.save()
        
        return Response({
            'message': 'Registration successful',
            'token': token_value,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'is_merchant': user.is_merchant,
                'merchant_name': user.merchant_name,
                'kyc_verified': user.kyc_verified,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': f'Registration failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def login(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        # Hash the provided password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Find user
        user = User.objects(username=username, password=hashed_password).first()
        if not user:
            
            user = User.objects(email=username, password=hashed_password).first()
        
        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Create or get existing token
        token = Token.objects(user=user).first()
        if not token:
            token_value = secrets.token_hex(32)
            token = Token(user=user, token=token_value)
            token.save()
        
        return Response({
            'message': 'Login successful',
            'token': token.token,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'is_merchant': user.is_merchant,
                'merchant_name': user.merchant_name,
                'kyc_verified': user.kyc_verified,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Login failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# User profile endpoint
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user
    return Response({
        'name': user.username,
        'email': user.email,
        'phone': getattr(user, 'phone', ''),
        'country': getattr(user, 'country', ''),
        'timezone': getattr(user, 'timezone', ''),
        'language': getattr(user, 'language', '')
    })

# User face photo endpoint
@api_view(['GET'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def user_face_photo(request):
    import base64
    user = request.user
    face_data = FaceData.objects(user=user).first()
    photo_b64 = ''
    return Response({'photo_b64': photo_b64})

# Portfolio and wallet management
@api_view(['GET'])
def get_portfolio(request):
    try:
        # Get user from token (simplified for now)
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        token_value = auth_header.replace('Bearer ', '')
        token = Token.objects(token=token_value).first()
        if not token:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = token.user
        portfolio = Portfolio.objects(user=user).first()
        
        if not portfolio:
            return Response({'error': 'Portfolio not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate current portfolio value
        total_value = calculate_portfolio_value(user)
        
        # Format wallet data with current values
        wallets_data = []
        for wallet in portfolio.wallets:
            wallet_value_usd = 0.0
            current_price = 0.0
            
            if wallet.symbol == 'USDT':
                wallet_value_usd = wallet.balance
                current_price = 1.0
            else:
                pair_name = f"{wallet.symbol}USDT"
                trading_pair = TradingPair.objects(pair=pair_name).first()
                if trading_pair:
                    current_price = trading_pair.current_price
                    wallet_value_usd = wallet.balance * current_price
            
            wallets_data.append({
                'symbol': wallet.symbol,
                'name': wallet.name,
                'balance': wallet.balance,
                'value_usd': wallet_value_usd,
                'current_price': current_price,
                'public_key': wallet.public_key,
                'is_active': wallet.is_active
            })
        
        return Response({
            'portfolio': {
                'total_value_usd': total_value,
                'wallets': wallets_data,
                'updated_at': portfolio.updated_at
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to get portfolio: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Trading and market data
@api_view(['GET'])
@permission_classes([AllowAny])
def price_history(request):
    """
    Returns price history for a given trading pair (e.g., BTCUSDT) for charting.
    Query param: pair=BTCUSDT
    Output: [{timestamp, price, volume}, ...]
    """
    pair_name = request.GET.get('pair', None)
    print(f"[price_history] Requested pair: {pair_name}")
    if not pair_name:
        print("[price_history] Missing pair parameter.")
        return Response({'error': 'Missing pair parameter.'}, status=400)
    trading_pair = TradingPair.objects(pair=pair_name).first()
    print(f"[price_history] TradingPair found: {trading_pair}")
    if not trading_pair:
        print(f"[price_history] Trading pair not found: {pair_name}")
        return Response({'error': 'Trading pair not found.'}, status=404)
    # Try to get last 100 price points from PriceHistory
    history_qs = PriceHistory.objects(pair=trading_pair).order_by('-timestamp')[:100]
    print(f"[price_history] PriceHistory count: {len(history_qs)}")
    if history_qs:
        history = [
            {
                'timestamp': ph.timestamp.strftime('%Y-%m-%d %H:%M'),
                'price': ph.price,
                'volume': ph.volume
            }
            for ph in reversed(history_qs)
        ]
        print(f"[price_history] Returning DB history, count: {len(history)}")
        return Response({'history': history}, status=200)
    # If no DB history, try CoinCap API v3 with API key
    import requests
    coincap_map = {
        'BTCUSDT': 'bitcoin',
        'ETHUSDT': 'ethereum',
        'LTCUSDT': 'litecoin',
        'BCHUSDT': 'bitcoin-cash',
        'DOGEUSDT': 'dogecoin',
        'BNBUSDT': 'binance-coin',
        'ADAUSDT': 'cardano',
        'DOTUSDT': 'polkadot',
        'LINKUSDT': 'chainlink',
        'ARCUSDT': 'arc'  # If listed on CoinCap
    }
    asset = coincap_map.get(pair_name)
    api_key = '62651e25b2334fea9dd4093de72720aadcb872020741570f813722c3346df9c0'
    if asset:
        try:
            url = f'https://rest.coincap.io/v3/assets/{asset}/history?interval=h1&apiKey={api_key}'
            resp = requests.get(url, timeout=10)
            data = resp.json()
            prices = data.get('data', [])
            # prices: [{priceUsd, time, ...}, ...]
            history = [
                {
                    'timestamp': datetime.utcfromtimestamp(int(row['time']/1000)).strftime('%Y-%m-%d %H:%M'),
                    'price': float(row['priceUsd']),
                    'volume': None
                }
                for row in prices[-100:] if 'priceUsd' in row and 'time' in row
            ]
            print(f"[price_history] Returning CoinCap v3 history, count: {len(history)}")
            return Response({'history': history}, status=200)
        except Exception as e:
            print(f"[price_history] CoinCap v3 error: {e}")
    # Fallback: generate runtime history from market data
    now = datetime.utcnow()
    points = []
    base_price = trading_pair.current_price
    for i in range(100):
        ts = now - timedelta(minutes=99-i)
        price = base_price * (1 + random.uniform(-0.01, 0.01))
        volume = trading_pair.volume_24h * random.uniform(0.8, 1.2) / 100
        points.append({
            'timestamp': ts.strftime('%Y-%m-%d %H:%M'),
            'price': round(price, 8),
            'volume': round(volume, 2)
        })
        base_price = price
    print(f"[price_history] Returning simulated history, count: {len(points)}")
    return Response({'history': points}, status=200)
@api_view(['GET'])
def get_market_data(request):
    try:
        # Simulate fresh prices
        updated_prices = simulate_all_prices()
        
        # Get all trading pairs
        pairs = TradingPair.objects(is_active=True)
        market_data = []
        
        for pair in pairs:
            market_data.append({
                'pair': pair.pair,
                'base_symbol': pair.base_symbol,
                'quote_symbol': pair.quote_symbol,
                'current_price': pair.current_price,
                'price_change_24h': pair.price_change_24h,
                'volume_24h': pair.volume_24h,
                'high_24h': pair.high_24h,
                'low_24h': pair.low_24h,
                'last_updated': pair.last_updated
            })
        
        return Response({'market_data': market_data}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to get market data: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def place_order(request):
    try:
        # Get user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        token_value = auth_header.replace('Bearer ', '')
        token = Token.objects(token=token_value).first()
        if not token:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = token.user
        
        # Extract order data
        pair_name = request.data.get('pair')
        order_type = request.data.get('order_type', 'market')
        side = request.data.get('side')
        quantity = float(request.data.get('quantity', 0))
        price = float(request.data.get('price', 0)) if request.data.get('price') else None
        
        if not all([pair_name, side, quantity]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
        
        if order_type == 'market':
            # Execute market order immediately
            success, message = execute_market_order(user, pair_name, side, quantity)
            if success:
                return Response({'message': message}, status=status.HTTP_200_OK)
            else:
                return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            # Create limit order (for future implementation)
            trading_pair = TradingPair.objects(pair=pair_name).first()
            if not trading_pair:
                return Response({'error': 'Trading pair not found'}, status=status.HTTP_404_NOT_FOUND)
            
            order = Order(
                user=user,
                pair=trading_pair,
                order_type=order_type,
                side=side,
                quantity=quantity,
                price=price,
                order_id=generate_order_id()
            )
            order.save()
            
            return Response({
                'message': 'Limit order placed successfully',
                'order_id': order.order_id
            }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': f'Failed to place order: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_order_history(request):
    try:
        # Get user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        token_value = auth_header.replace('Bearer ', '')
        token = Token.objects(token=token_value).first()
        if not token:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = token.user
        
        # Get orders for this user
        orders = Order.objects(user=user).order_by('-created_at')[:50]  # Last 50 orders
        
        orders_data = []
        for order in orders:
            orders_data.append({
                'order_id': order.order_id,
                'pair': order.pair.pair,
                'order_type': order.order_type,
                'side': order.side,
                'quantity': order.quantity,
                'price': order.price,
                'filled_quantity': order.filled_quantity,
                'status': order.status,
                'created_at': order.created_at,
                'updated_at': order.updated_at
            })
        
        return Response({'orders': orders_data}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to get order history: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Curve Cart Integration
@api_view(['POST'])
def create_curve_cart(request):
    try:
        # Get user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        token_value = auth_header.replace('Bearer ', '')
        token = Token.objects(token=token_value).first()
        if not token:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = token.user
        
        # Extract cart data
        items = request.data.get('items', [])
        total_amount = float(request.data.get('total_amount', 0))
        merchant_name = request.data.get('merchant_name', 'curve')
        
        # Ensure Curve merchant exists
        merchant = MerchantWallet.objects(merchant_name=merchant_name).first()
        if not merchant:
            # Create Curve merchant
            merchant_user = User.objects(username=merchant_name).first()
            if not merchant_user:
                merchant_user = User(
                    username=merchant_name,
                    email=f"{merchant_name}@curve.com",
                    password=hashlib.sha256("curve_default".encode()).hexdigest(),
                    is_merchant=True,
                    merchant_name=merchant_name
                )
                merchant_user.save()
            
            merchant = MerchantWallet(
                merchant_name=merchant_name,
                user=merchant_user,
                business_name="Curve E-commerce",
                website_url="https://curve.com"
            )
            
            # Create merchant wallets
            for crypto in ['BTC', 'ETH', 'ARC', 'USDT', 'SOL']:
                public_key, private_key = generate_wallet()
                wallet = CryptoWallet(
                    symbol=crypto,
                    name=get_crypto_name(crypto),
                    public_key=public_key,
                    private_key=json.dumps(private_key),
                    balance=0.0
                )
                merchant.wallets.append(wallet)
            
            merchant.save()
        
        # Create cart
        cart = CurveCart(
            user=user,
            items=items,
            total_amount=total_amount,
            merchant=merchant,
            cart_id=f"CART_{int(datetime.utcnow().timestamp())}_{random.randint(1000, 9999)}"
        )
        cart.save()
        
        return Response({
            'message': 'Cart created successfully',
            'cart_id': cart.cart_id,
            'merchant_wallets': [
                {
                    'symbol': wallet.symbol,
                    'address': wallet.public_key
                } for wallet in merchant.wallets
            ]
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': f'Failed to create cart: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def process_curve_payment(request):
    try:
        cart_id = request.data.get('cart_id')
        crypto_symbol = request.data.get('crypto_symbol')
        
        cart = CurveCart.objects(cart_id=cart_id).first()
        if not cart:
            return Response({'error': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if cart.status != 'pending':
            return Response({'error': 'Cart already processed'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate crypto amount needed
        pair_name = f"{crypto_symbol}USDT"
        trading_pair = TradingPair.objects(pair=pair_name).first()
        if not trading_pair:
            return Response({'error': 'Crypto not supported'}, status=status.HTTP_400_BAD_REQUEST)
        
        crypto_amount = cart.total_amount / trading_pair.current_price
        
        # Process transfer from user to merchant
        success, message = process_crypto_transfer(
            cart.user,
            cart.merchant.user,
            crypto_symbol,
            crypto_amount,
            f"Payment for cart {cart_id}"
        )
        
        if success:
            # Update cart status
            cart.status = 'paid'
            cart.crypto_payment = {
                'symbol': crypto_symbol,
                'amount': crypto_amount,
                'tx_hash': generate_transaction_hash()
            }
            cart.updated_at = datetime.utcnow()
            cart.save()
            
            # Update merchant total received
            cart.merchant.total_received += cart.total_amount
            cart.merchant.save()
            
            return Response({
                'message': 'Payment processed successfully',
                'transaction_hash': cart.crypto_payment['tx_hash'],
                'crypto_amount': crypto_amount
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({'error': f'Payment processing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Transaction history
@api_view(['GET', 'POST'])
def get_transaction_history(request):
    if request.method == 'GET':
        return handle_get_transactions(request)
    elif request.method == 'POST':
        return handle_create_transaction(request)

def handle_get_transactions(request):
    try:
        # Get user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        token_value = auth_header.replace('Bearer ', '')
        token = Token.objects(token=token_value).first()
        if not token:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = token.user
        
        # Get transactions for this user
        transactions = Transaction.objects(user=user).order_by('-created_at')[:100]  # Last 100 transactions
        
        transactions_data = []
        for tx in transactions:
            transactions_data.append({
                'tx_hash': tx.tx_hash,
                'transaction_type': tx.transaction_type,
                'crypto_symbol': tx.crypto_symbol,
                'amount': tx.amount,
                'to_address': tx.to_address,
                'from_address': tx.from_address,
                'status': tx.status,
                'fee': tx.fee,
                'memo': tx.memo,
                'created_at': tx.created_at
            })
        
        return Response({'transactions': transactions_data}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to get transaction history: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def handle_create_transaction(request):
    try:
        # Get user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        token_value = auth_header.replace('Bearer ', '')
        token = Token.objects(token=token_value).first()
        if not token:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = token.user
        
        # Get transaction data from request
        to_address = request.data.get('to_address')
        amount = float(request.data.get('amount', 0))
        crypto_symbol = request.data.get('crypto_symbol', 'ARC')
        transaction_type = request.data.get('transaction_type', 'transfer')
        memo = request.data.get('memo', '')
        
        if not to_address or amount <= 0:
            return Response({'error': 'Invalid transaction data'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user's portfolio to check balance
        portfolio = Portfolio.objects(user=user).first()
        if not portfolio:
            return Response({'error': 'Portfolio not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Find the wallet for the specified crypto
        wallet = None
        for w in portfolio.wallets:
            if w.symbol == crypto_symbol:
                wallet = w
                break
        
        if not wallet:
            return Response({'error': f'{crypto_symbol} wallet not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user has sufficient balance
        if wallet.balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create transaction
        import uuid
        tx_hash = str(uuid.uuid4())
        
        transaction = Transaction(
            user=user,
            tx_hash=tx_hash,
            transaction_type=transaction_type,
            crypto_symbol=crypto_symbol,
            amount=amount,
            to_address=to_address,
            from_address=wallet.public_key,
            status='confirmed',
            fee=0.001,  # Small fee
            memo=memo
        )
        transaction.save()
        
        # Update wallet balance
        wallet.balance -= amount
        portfolio.save()
        
        # Return transaction details
        return Response({
            'transaction': {
                'tx_hash': transaction.tx_hash,
                'transaction_type': transaction.transaction_type,
                'crypto_symbol': transaction.crypto_symbol,
                'amount': transaction.amount,
                'to_address': transaction.to_address,
                'from_address': transaction.from_address,
                'status': transaction.status,
                'fee': transaction.fee,
                'memo': transaction.memo,
                'created_at': transaction.created_at
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': f'Failed to create transaction: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def cancel_transaction(request):
    try:
        user = request.user
        tx_hash = request.data.get('tx_hash')
        
        if not tx_hash:
            return Response({'error': 'Transaction hash required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the transaction
        transaction = Transaction.objects(user=user, tx_hash=tx_hash).first()
        if not transaction:
            return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Only allow cancellation of pending transactions
        if transaction.status != 'pending':
            return Response({'error': 'Only pending transactions can be cancelled'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update transaction status to failed
        transaction.status = 'failed'
        transaction.memo = (transaction.memo or '') + ' [CANCELLED BY USER]'
        transaction.save()
        
        # Refund the amount to user's wallet if it was already deducted
        portfolio = Portfolio.objects(user=user).first()
        if portfolio:
            for wallet in portfolio.wallets:
                if wallet.symbol == transaction.crypto_symbol:
                    wallet.balance += transaction.amount
                    portfolio.save()
                    break
        
        return Response({
            'message': 'Transaction cancelled successfully',
            'transaction': {
                'tx_hash': transaction.tx_hash,
                'status': transaction.status
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to cancel transaction: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Initialize system
@api_view(['POST'])
def initialize_system(request):
    try:
        # Initialize trading pairs
        initialize_trading_pairs()
        
        # Simulate initial prices
        simulate_all_prices()
        
        # Initialize merchant wallets for all merchants
        initialize_merchant_wallets()
        
        return Response({'message': 'System initialized successfully'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'System initialization failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def initialize_merchant_wallets():
    """Initialize merchant wallets for all merchant users"""
    try:
        merchant_users = User.objects(is_merchant=True)
        
        for merchant_user in merchant_users:
            # Check if merchant wallet already exists
            existing_wallet = MerchantWallet.objects(user=merchant_user).first()
            if existing_wallet:
                continue
                
            # Create merchant wallet with crypto wallets
            merchant_wallets = []
            
            # Create wallets for each supported crypto
            supported_cryptos = [
                ('ARC', 'Arc Token'),
                ('BTC', 'Bitcoin'),
                ('ETH', 'Ethereum'),
                ('USDT', 'Tether'),
                ('BNB', 'Binance Coin')
            ]
            
            for symbol, name in supported_cryptos:
                public_key, private_key_list = generate_wallet()
                crypto_wallet = CryptoWallet(
                    symbol=symbol,
                    name=name,
                    public_key=public_key,
                    private_key=json.dumps(private_key_list),
                    balance=1000.0 if symbol == 'ARC' else 0.0,  # Give merchants some initial ARC
                    is_active=True
                )
                merchant_wallets.append(crypto_wallet)
            
            # Create merchant wallet document
            merchant_wallet = MerchantWallet(
                merchant_name=merchant_user.merchant_name or merchant_user.username,
                user=merchant_user,
                wallets=merchant_wallets,
                business_name=merchant_user.merchant_name or f"{merchant_user.username} Business",
                is_active=True
            )
            merchant_wallet.save()
            
            print(f"Created merchant wallet for {merchant_user.username}")
            
    except Exception as e:
        print(f"Error initializing merchant wallets: {e}")
        raise e

# Legacy endpoints for backward compatibility
@api_view(['GET'])
def get_wallet(request):
    try:
        username = request.GET.get('username')
        crypto = request.GET.get('crypto', 'SOL')
        
        user = User.objects(username=username).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        portfolio = Portfolio.objects(user=user).first()
        if not portfolio:
            return Response({'error': 'Portfolio not found'}, status=status.HTTP_404_NOT_FOUND)
        
        for wallet in portfolio.wallets:
            if wallet.symbol == crypto:
                return Response({
                    'public_key': wallet.public_key,
                    'balance': wallet.balance,
                    'symbol': wallet.symbol
                }, status=status.HTTP_200_OK)
        
        return Response({'error': f'{crypto} wallet not found'}, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        return Response({'error': f'Failed to get wallet: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'error': 'Email already exists.'}, status=400)

    # Create user
    user = User(username=username, email=email, password=password, created_at=datetime.utcnow())
    user.save()

    # Create portfolio with initial ARC wallet
    public_key, private_key_list = generate_wallet()
    arc_wallet = CryptoWallet(
        symbol='ARC',
        name='Arc Token',
        public_key=public_key,
        private_key=json.dumps(private_key_list),
        balance=1000.0,
        network='Solana Devnet'
    )
    portfolio = Portfolio(user=user, wallets=[arc_wallet])
    portfolio.save()

    # Register face data if image provided
    if image_file:
        image = face_recognition.load_image_file(image_file)
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            print("No face found in image.")
            return Response({'error': 'No face found in image.'}, status=400)
        encoding_array = encodings[0]
        face_data = FaceData(user=user, encoding=encoding_array.tobytes())
        face_data.save()

    # Generate a simple token and save to database
    token = secrets.token_hex(32)
    token_obj = Token(user=user, token=token)
    token_obj.save()

    return Response({
        'user': {'id': str(user.id), 'username': username, 'email': email},
        'wallet': {
            'public_key': public_key,
            'balance': arc_wallet.balance,
            'network': arc_wallet.network
        },
        'token': token
    })

@api_view(['POST'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_wallet(request):
    user = request.user
    symbol = request.data.get('symbol', 'BTC')
    name = request.data.get('name', 'Bitcoin')
    
    portfolio = Portfolio.objects(user=user).first()
    if not portfolio:
        portfolio = Portfolio(user=user, wallets=[])
        portfolio.save()
    
    # Check if wallet for this symbol already exists
    for wallet in portfolio.wallets:
        if wallet.symbol == symbol:
            return Response({'error': f'{symbol} wallet already exists.'}, status=400)
    
    public_key, private_key_list = generate_wallet()
    new_wallet = CryptoWallet(
        symbol=symbol,
        name=name,
        public_key=public_key,
        private_key=json.dumps(private_key_list),
        balance=0.0,
        network='mainnet'
    )
    
    portfolio.wallets.append(new_wallet)
    portfolio.save()
    
    return Response({
        'wallet': {
            'symbol': symbol,
            'name': name,
            'public_key': public_key,
            'balance': new_wallet.balance,
            'network': new_wallet.network
        }
    })



@api_view(['GET'])
@permission_classes([AllowAny])
def get_wallet_by_id(request, user_id):
    user = User.objects(id=user_id).first()
    if not user:
        return Response({'error': 'User not found.'}, status=404)
    
    portfolio = Portfolio.objects(user=user).first()
    if not portfolio or not portfolio.wallets:
        return Response({'error': 'No wallet found.'}, status=404)
    
    # Return the first wallet (ARC wallet) for backward compatibility
    wallet = portfolio.wallets[0]
    
    return Response({
        'wallet': {
            'public_key': wallet.public_key, 
            'balance': wallet.balance, 
            'network': wallet.network,
            'symbol': wallet.symbol,
            'name': wallet.name
        }
    })

@api_view(['POST'])
def register_face(request):
    user_id = request.data.get("user_id")
    image_file = request.FILES.get("image")

    if not image_file:
        return Response({"error": "No image provided."}, status=400)

    image = face_recognition.load_image_file(image_file)
    encodings = face_recognition.face_encodings(image)

    if not encodings:
        return Response({"error": "No face found in image."}, status=400)

    encoding_array = encodings[0]
    user = User.objects.get(id=user_id)
    FaceData.objects.update_or_create(user=user, defaults={
        "encoding": encoding_array.tobytes()
    })
    return Response({"message": "Face registered."})



# Remove Solana-related imports
# from solders.keypair import Keypair
# from solana.rpc.api import Client
# from solana.transaction import Transaction
# from solana.system_program import transfer, TransferParams
# from solana.publickey import PublicKey

# Remove any Solana client or transaction code (already replaced by dummy logic)

@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    # This view is tied to Django ORM TokenAuthentication.
    # For a stateless token, you'd invalidate it here.
    # For this demo, we'll just remove it from the in-memory store.
    # In a real app, you'd use a JWT or similar.
    token_key = request.headers.get('Authorization', '').replace('Token ', '')
    if token_key in USER_TOKENS:
        del USER_TOKENS[token_key]
    return Response({'message': 'Logged out successfully.'})

@api_view(['GET'])
@permission_classes([AllowAny])
def user_info(request):
    try:
        custom_user = User.objects.get(username=request.user.username)
        portfolio = Portfolio.objects(user=custom_user).first()
        wallet_data = None
        if portfolio and portfolio.wallets:
            wallet = portfolio.wallets[0]  # First wallet for backward compatibility
            wallet_data = {
                'symbol': wallet.symbol,
                'name': wallet.name,
                'public_key': wallet.public_key,
                'balance': wallet.balance,
                'network': wallet.network
            }
        return Response({
            'username': custom_user.username,
            'email': custom_user.email,
            'wallet': wallet_data
        })
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)

@api_view(['GET'])
@permission_classes([AllowAny])
def wallet_info(request):
    try:
        custom_user = User.objects.get(username=request.user.username)
        portfolio = Portfolio.objects(user=custom_user).first()
        if not portfolio or not portfolio.wallets:
            return Response({'error': 'No wallet found.'}, status=404)
        
        wallet = portfolio.wallets[0]  # First wallet for backward compatibility
        return Response({
            'symbol': wallet.symbol,
            'name': wallet.name,
            'public_key': wallet.public_key,
            'balance': wallet.balance,
            'network': wallet.network
        })
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)

@api_view(['GET'])
@permission_classes([AllowAny])
def crypto_list(request):
    # Dummy supported cryptos
    return Response({
        'cryptos': [
            {'symbol': 'DUM', 'name': 'DummyCoin'},
            {'symbol': 'BTC', 'name': 'Bitcoin (Simulated)'},
            {'symbol': 'ETH', 'name': 'Ethereum (Simulated)'}
        ]
    })

@api_view(['POST'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    user = request.user
    portfolio = Portfolio.objects(user=user).first()
    if not portfolio or not portfolio.wallets:
        return Response({'error': 'No wallet found.'}, status=404)
        
    to_address = request.data.get('to_address')
    amount = float(request.data.get('amount', 0))
    symbol = request.data.get('symbol', 'ARC')  # Default to ARC
    
    # Find the specific wallet by symbol
    wallet = None
    for w in portfolio.wallets:
        if w.symbol == symbol:
            wallet = w
            break
    
    if not wallet:
        return Response({'error': f'No {symbol} wallet found.'}, status=404)
        
    # Dummy face auth check (should be improved)
    face_ok = request.data.get('face_ok', False)
    if not face_ok:
        return Response({'error': 'Face authentication failed.'}, status=403)
    if wallet.balance < amount:
        return Response({'error': 'Insufficient balance.'}, status=400)
        
    wallet.balance -= amount
    portfolio.save()
    
    # Create transaction record
    txn = Transaction(
        user=user,
        transaction_type='transfer',
        crypto_symbol=symbol,
        amount=amount,
        to_address=to_address,
        status='confirmed'
    )
    txn.save()
    
    return Response({'message': 'Payment successful', 'transaction_id': str(txn.id)})

@api_view(['GET'])
@permission_classes([AllowAny])
def payment_status(request):
    try:
        custom_user = User.objects.get(username=request.user.username)
        txn_id = request.query_params.get('transaction_id')
        # txn = Transaction.objects.filter(id=txn_id, wallet__user=custom_user).first()
        if not txn_id:
            return Response({'error': 'Transaction ID not provided.'}, status=400)
        return Response({'status': 'success', 'amount': 100.0, 'to_address': 'dummy_address', 'timestamp': datetime.utcnow().isoformat()})
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)

@api_view(['GET'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def transaction_history(request):
    user = request.user
    portfolio = Portfolio.objects(user=user).first()
    if not portfolio:
        return Response({'error': 'No portfolio found.'}, status=404)
        
    txns = Transaction.objects(user=user).order_by('-created_at')
    txn_list = [
        {
            'id': str(txn.id),
            'to_address': txn.to_address,
            'amount': txn.amount,
            'symbol': txn.crypto_symbol,
            'type': txn.transaction_type,
            'timestamp': txn.created_at,
            'status': txn.status
        }
        for txn in txns
    ]
    return Response({'transactions': txn_list})

@api_view(['POST'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def face_auth(request):
    user = request.user
    image_file = request.FILES.get('image')
    if not image_file:
        return Response({'error': 'No image provided.'}, status=400)
    face_data = FaceData.objects(user=user).first()
    if not face_data:
        return Response({'error': 'No face data registered.'}, status=404)
    image = face_recognition.load_image_file(image_file)
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        return Response({'error': 'No face found in image.'}, status=400)
    encoding_array = encodings[0]
    stored_encoding = np.frombuffer(face_data.encoding, dtype=np.float64)
    match = face_recognition.compare_faces([stored_encoding], encoding_array)[0]
    return Response({'face_ok': match})

@api_view(['POST'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def buy_crypto(request):
    user = request.user
    portfolio = Portfolio.objects(user=user).first()
    if not portfolio:
        return Response({'error': 'No portfolio found.'}, status=404)
        
    amount = float(request.data.get('amount', 0))
    symbol = request.data.get('symbol', 'ARC')
    
    if amount <= 0:
        return Response({'error': 'Invalid amount.'}, status=400)
    
    # Find the specific wallet by symbol
    wallet = None
    for w in portfolio.wallets:
        if w.symbol == symbol:
            wallet = w
            break
    
    if not wallet:
        return Response({'error': f'No {symbol} wallet found.'}, status=404)
        
    wallet.balance += amount
    portfolio.save()
    
    # Create transaction record
    txn = Transaction(
        user=user,
        transaction_type='deposit',
        crypto_symbol=symbol,
        amount=amount,
        status='confirmed'
    )
    txn.save()
    
    return Response({'message': 'Crypto bought successfully.', 'balance': wallet.balance})

@api_view(['POST'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def sell_crypto(request):
    user = request.user
    portfolio = Portfolio.objects(user=user).first()
    if not portfolio:
        return Response({'error': 'No portfolio found.'}, status=404)
        
    amount = float(request.data.get('amount', 0))
    symbol = request.data.get('symbol', 'ARC')
    
    if amount <= 0:
        return Response({'error': 'Invalid amount.'}, status=400)
    
    # Find the specific wallet by symbol
    wallet = None
    for w in portfolio.wallets:
        if w.symbol == symbol:
            wallet = w
            break
    
    if not wallet:
        return Response({'error': f'No {symbol} wallet found.'}, status=404)
        
    if wallet.balance < amount:
        return Response({'error': 'Insufficient balance.'}, status=400)
        
    wallet.balance -= amount
    portfolio.save()
    
    # Create transaction record
    txn = Transaction(
        user=user,
        transaction_type='withdraw',
        crypto_symbol=symbol,
        amount=amount,
        status='confirmed'
    )
    txn.save()
    
    return Response({'message': 'Crypto sold successfully.', 'balance': wallet.balance})

@api_view(['POST'])
@authentication_classes([SimpleTokenAuthentication])
@permission_classes([IsAuthenticated])
def transfer_to_merchant(request):
    user = request.user
    portfolio = Portfolio.objects(user=user).first()
    if not portfolio:
        return Response({'error': 'No portfolio found.'}, status=404)
        
    merchant_name = request.data.get('merchant_name')
    amount = float(request.data.get('amount', 0))
    symbol = request.data.get('symbol', 'ARC')
    face_ok = request.data.get('face_ok', False)
    
    if not merchant_name or amount <= 0:
        return Response({'error': 'Invalid merchant or amount.'}, status=400)
    if not face_ok:
        return Response({'error': 'Face authentication failed.'}, status=403)
    
    # Find user's wallet
    user_wallet = None
    for w in portfolio.wallets:
        if w.symbol == symbol:
            user_wallet = w
            break
    
    if not user_wallet:
        return Response({'error': f'No {symbol} wallet found.'}, status=404)
        
    if user_wallet.balance < amount:
        return Response({'error': 'Insufficient balance.'}, status=400)
    
    merchant_wallet = MerchantWallet.objects(merchant_name=merchant_name).first()
    if not merchant_wallet:
        return Response({'error': 'Merchant wallet not found.'}, status=404)
    
    # Find or create merchant's crypto wallet
    merchant_crypto_wallet = None
    for w in merchant_wallet.wallets:
        if w.symbol == symbol:
            merchant_crypto_wallet = w
            break
    
    if not merchant_crypto_wallet:
        # Create new crypto wallet for merchant
        public_key, private_key_list = generate_wallet()
        merchant_crypto_wallet = CryptoWallet(
            symbol=symbol,
            name=f'{symbol} Wallet',
            public_key=public_key,
            private_key=json.dumps(private_key_list),
            balance=0.0,
            network='mainnet'
        )
        merchant_wallet.wallets.append(merchant_crypto_wallet)
    
    # Transfer
    user_wallet.balance -= amount
    merchant_crypto_wallet.balance += amount
    portfolio.save()
    merchant_wallet.save()
    
    txn = Transaction(
        user=user,
        transaction_type='transfer',
        crypto_symbol=symbol,
        amount=amount,
        to_address=merchant_crypto_wallet.public_key,
        status='confirmed'
    )
    txn.save()
    
    return Response({'message': 'Payment successful', 'transaction_id': str(txn.id)})

@api_view(['POST'])
@permission_classes([AllowAny])
def create_merchant_wallet(request):
    merchant_name = request.data.get('merchant_name')
    if not merchant_name:
        return Response({'error': 'Merchant name required.'}, status=400)
    if MerchantWallet.objects(merchant_name=merchant_name).first():
        return Response({'error': 'Merchant wallet already exists.'}, status=400)
    
    # Create initial ARC wallet for merchant
    public_key, private_key_list = generate_wallet()
    arc_wallet = CryptoWallet(
        symbol='ARC',
        name='Arc Token',
        public_key=public_key,
        private_key=json.dumps(private_key_list),
        balance=0.0,
        network='Solana Devnet'
    )
    
    merchant_wallet = MerchantWallet(
        merchant_name=merchant_name,
        wallets=[arc_wallet],
        is_active=True
    )
    merchant_wallet.save()
    
    return Response({'merchant_wallet': {
        'merchant_name': merchant_name,
        'public_key': public_key,
        'balance': arc_wallet.balance,
        'network': arc_wallet.network
    }})

# Auto-create curve-merchant wallet if it doesn't exist
def ensure_curve_merchant_exists():
    if not MerchantWallet.objects(merchant_name='curve-merchant').first():
        # First create a merchant user
        merchant_user = User.objects(username='curve-merchant').first()
        if not merchant_user:
            merchant_user = User(
                username='curve-merchant',
                email='merchant@curve.com',
                password=hashlib.sha256("curve_default".encode()).hexdigest(),
                is_merchant=True,
                merchant_name='curve-merchant',
                kyc_verified=True
            )
            merchant_user.save()
        
        public_key, private_key_list = generate_wallet()
        arc_wallet = CryptoWallet(
            symbol='ARC',
            name='Arc Token',
            public_key=public_key,
            private_key=json.dumps(private_key_list),
            balance=0.0,
            network='Solana Devnet'
        )
        merchant_wallet = MerchantWallet(
            merchant_name='curve-merchant',
            user=merchant_user,
            wallets=[arc_wallet],
            business_name='Curve Marketplace',
            website_url='https://curve.example.com',
            is_active=True
        )
        merchant_wallet.save()
        print("Created curve-merchant wallet")

# Comment out the auto-call for now to avoid module load issues
# try:
#     ensure_curve_merchant_exists()
# except Exception as e:
#     print(f"Error creating curve-merchant: {e}")

@api_view(['GET'])
@permission_classes([AllowAny])
def get_merchant_wallet(request, merchant_name):
    merchant_wallet = MerchantWallet.objects(merchant_name=merchant_name).first()
    if not merchant_wallet:
        return Response({'error': 'Merchant wallet not found.'}, status=404)
    
    # Return the first wallet (ARC wallet) for backward compatibility
    if merchant_wallet.wallets:
        wallet = merchant_wallet.wallets[0]
        return Response({'merchant_wallet': {
            'merchant_name': merchant_wallet.merchant_name,
            'public_key': wallet.public_key,
            'balance': wallet.balance,
            'network': wallet.network,
            'symbol': wallet.symbol
        }})
    else:
        return Response({'error': 'No wallets found for this merchant.'}, status=404)



@api_view(["GET"])
@permission_classes([AllowAny])
def get_order_book(request):
    symbol = request.query_params.get("symbol", "ARC")
    pair_name = f"{symbol}USDT"
    
    # Get trading pair
    trading_pair = TradingPair.objects(pair=pair_name).first()
    if not trading_pair:
        return Response({"orders": []})
    
    orders = Order.objects(pair=trading_pair, status="pending").order_by("-created_at")
    order_list = [
        {
            "id": str(o.id),
            "type": o.order_type,
            "side": o.side,
            "symbol": symbol,
            "price": o.price,
            "quantity": o.quantity,
            "timestamp": o.created_at,
        }
        for o in orders
    ]
    return Response({"orders": order_list})

@api_view(["GET"])
@permission_classes([AllowAny])
def get_prices(request):
    # Simulate prices for each symbol
    prices = {s: round(random.uniform(10, 100), 2) for s in SYMBOLS}
    return Response({"prices": prices})

@api_view(['GET'])
@permission_classes([AllowAny])
def debug_auth(request):
    """Debug endpoint to check authentication status"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', 'No auth header')
    user = getattr(request, 'user', 'No user')
    user_type = type(user).__name__
    
    # Check if token exists in database
    token_exists = False
    total_tokens = Token.objects.count()
    
    if auth_header.startswith('Token '):
        token = auth_header[6:]
        token_obj = Token.objects(token=token).first()
        token_exists = token_obj is not None
    
    return Response({
        'auth_header': auth_header,
        'user': str(user),
        'user_type': user_type,
        'token_exists_in_db': token_exists,
        'total_tokens_in_db': total_tokens
    })

# Merchant Payment Endpoints
@api_view(['GET'])
@permission_classes([AllowAny])
def get_merchant_info(request):
    """Get merchant wallet info for payments"""
    try:
        merchant_name = request.GET.get('merchant_name', 'curve-merchant')
        
        # Find merchant by name or merchant_name field
        merchant_wallet = MerchantWallet.objects(merchant_name=merchant_name).first()
        if not merchant_wallet:
            # Try to find by user.merchant_name for backwards compatibility
            merchant_user = User.objects(merchant_name=merchant_name, is_merchant=True).first()
            if merchant_user:
                merchant_wallet = MerchantWallet.objects(user=merchant_user).first()
        
        if not merchant_wallet or not merchant_wallet.is_active:
            return Response({'error': 'Merchant not found or inactive'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get merchant's wallet addresses for each supported crypto
        wallet_addresses = {}
        for wallet in merchant_wallet.wallets:
            if wallet.is_active:
                wallet_addresses[wallet.symbol] = wallet.public_key
        
        return Response({
            'merchant_name': merchant_wallet.merchant_name,
            'business_name': merchant_wallet.business_name,
            'user_id': str(merchant_wallet.user.id),
            'wallet_addresses': wallet_addresses,
            'is_active': merchant_wallet.is_active
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Failed to get merchant info: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def process_merchant_payment(request):
    """Process payment from user to merchant"""
    try:
        # Get user from token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        token_value = auth_header.replace('Bearer ', '')
        token = Token.objects(token=token_value).first()
        if not token:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = token.user
        
        # Get payment data
        merchant_name = request.data.get('merchant_name', 'curve-merchant')
        amount = float(request.data.get('amount', 0))
        crypto_symbol = request.data.get('crypto_symbol', 'ARC')
        memo = request.data.get('memo', f'Payment to {merchant_name}')
        
        if amount <= 0:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find merchant
        merchant_wallet = MerchantWallet.objects(merchant_name=merchant_name).first()
        if not merchant_wallet:
            merchant_user = User.objects(merchant_name=merchant_name, is_merchant=True).first()
            if merchant_user:
                merchant_wallet = MerchantWallet.objects(user=merchant_user).first()
        
        if not merchant_wallet or not merchant_wallet.is_active:
            return Response({'error': 'Merchant not found or inactive'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get merchant wallet address for the crypto
        merchant_crypto_wallet = None
        for wallet in merchant_wallet.wallets:
            if wallet.symbol == crypto_symbol and wallet.is_active:
                merchant_crypto_wallet = wallet
                break
        
        if not merchant_crypto_wallet:
            return Response({'error': f'Merchant does not accept {crypto_symbol}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process the transfer
        success, message = process_crypto_transfer(
            user,
            merchant_wallet.user,
            crypto_symbol,
            amount,
            memo
        )
        
        if success:
            # Update merchant total received
            # Get current price for USD conversion
            pair_name = f"{crypto_symbol}USDT"
            trading_pair = TradingPair.objects(pair=pair_name).first()
            usd_value = amount
            if trading_pair:
                usd_value = amount * trading_pair.current_price
            
            merchant_wallet.total_received += usd_value
            merchant_wallet.save()
            
            # Generate transaction hash
            tx_hash = generate_transaction_hash()
            
            return Response({
                'message': 'Payment processed successfully',
                'transaction_hash': tx_hash,
                'amount': amount,
                'crypto_symbol': crypto_symbol,
                'merchant_address': merchant_crypto_wallet.public_key,
                'usd_value': usd_value
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({'error': f'Failed to process payment: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

