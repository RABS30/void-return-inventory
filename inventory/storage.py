# Temporary JSON Storage for Demo
# This will be replaced with database models in production

import json
import os
from django.conf import settings

STORAGE_DIR = os.path.join(settings.BASE_DIR, 'demo_storage')
TRANSACTIONS_FILE = os.path.join(STORAGE_DIR, 'transactions.json')

# Create storage directory if not exists
os.makedirs(STORAGE_DIR, exist_ok=True)

def load_transactions():
    """Load transactions from JSON file"""
    if not os.path.exists(TRANSACTIONS_FILE):
        # Initialize with dummy data
        dummy_data = [
            {
                'id': 1,
                'tanggal': '2026-09-21',
                'outlet': 'BT5',
                'barcode': '8992388101010',
                'namaBarang': 'Indomie Goreng 85g',
                'quantity': 2,
                'tipe': 'void',
                'kasir': 'Siti Aminah',
                'otoritas': 'Budi Santoso',
                'alasan': 'Kasir salah input jumlah',
                'notrans': None,
                'hjual': None,
                'foto': None
            },
            {
                'id': 2,
                'tanggal': '2026-09-21',
                'outlet': 'BT3',
                'barcode': '8993675610019',
                'namaBarang': 'Aqua Botol 600ml',
                'quantity': 1,
                'tipe': 'return',
                'kasir': 'Dewi Lestari',
                'otoritas': 'Ahmad Rifai',
                'alasan': 'Kemasan bocor',
                'notrans': 'TRX20260921001',
                'hjual': 4000,
                'foto': 'struk_001.jpg'
            },
            {
                'id': 3,
                'tanggal': '2026-09-20',
                'outlet': 'BT7',
                'barcode': '8996001600016',
                'namaBarang': 'Teh Pucuk Harum 350ml',
                'quantity': 3,
                'tipe': 'void',
                'kasir': 'Rina Wati',
                'otoritas': 'Hendra Kusuma',
                'alasan': 'Pembeli batal beli',
                'notrans': None,
                'hjual': None,
                'foto': None
            },
            {
                'id': 4,
                'tanggal': '2026-09-19',
                'outlet': 'BT12',
                'barcode': '8998866123456',
                'namaBarang': 'Chitato Sapi Panggang 68g',
                'quantity': 1,
                'tipe': 'return',
                'kasir': 'Doni Pratama',
                'otoritas': 'Sri Wahyuni',
                'alasan': 'Salah rasa, ditukar',
                'notrans': 'TRX20260919045',
                'hjual': 8500,
                'foto': 'struk_002.jpg'
            },
            {
                'id': 5,
                'tanggal': '2026-09-20',
                'outlet': 'BT2',
                'barcode': '8991001234567',
                'namaBarang': 'Mie Sedaap Goreng 85g',
                'quantity': 5,
                'tipe': 'void',
                'kasir': 'Indah Permata',
                'otoritas': 'Bambang Wijaya',
                'alasan': 'Sistem error saat transaksi',
                'notrans': None,
                'hjual': None,
                'foto': None
            },
            {
                'id': 6,
                'tanggal': '2026-09-18',
                'outlet': 'BT15',
                'barcode': '8992761111111',
                'namaBarang': 'Ultra Milk Coklat 200ml',
                'quantity': 2,
                'tipe': 'return',
                'kasir': 'Fitri Handayani',
                'otoritas': 'Agus Salim',
                'alasan': 'Produk mendekati kadaluarsa',
                'notrans': 'TRX20260918012',
                'hjual': 5500,
                'foto': 'struk_003.jpg'
            }
        ]
        save_transactions(dummy_data)
        return dummy_data
    
    with open(TRANSACTIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_transactions(transactions):
    """Save transactions to JSON file"""
    with open(TRANSACTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(transactions, f, ensure_ascii=False, indent=2)

def get_next_id():
    """Get next available ID"""
    transactions = load_transactions()
    if not transactions:
        return 1
    return max(t['id'] for t in transactions) + 1
