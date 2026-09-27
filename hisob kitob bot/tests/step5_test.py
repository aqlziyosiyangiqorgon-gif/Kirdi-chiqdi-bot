import sys
from pathlib import Path

# Parent path ga qo'shish
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.voice_service import parse_financial_voice_text

def main():
    print("--- 5-BOSQICH (OVOZLI PARSER UNIT TEST) BOSHLANDI ---")
    
    mock_categories = [
        {"id": 1, "name": "Do'kon", "type": "expense"},
        {"id": 2, "name": "Benzin", "type": "expense"},
        {"id": 3, "name": "Oylik", "type": "income"}
    ]
    
    mock_accounts = [
        {"id": 10, "name": "Naqd", "balance": 500000.0},
        {"id": 11, "name": "Uzcard", "balance": 1500000.0}
    ]

    # Test case 1: Expense with 'ming' and explicit account
    phrase1 = "Do'kondan 150 mingga go'sht oldim naqdga"
    parsed1 = parse_financial_voice_text(phrase1, mock_categories, mock_accounts)
    print(f"[+] Phrase 1: '{phrase1}' -> {parsed1}")
    assert parsed1 is not None
    assert parsed1["amount"] == 150000.0
    assert parsed1["type"] == "expense"
    assert parsed1["category_name"] == "Do'kon"
    assert parsed1["account_name"] == "Naqd"

    # Test case 2: Income with 'million' and account
    phrase2 = "Oylikdan 2 million tushdi uzcardga"
    parsed2 = parse_financial_voice_text(phrase2, mock_categories, mock_accounts)
    print(f"[+] Phrase 2: '{phrase2}' -> {parsed2}")
    assert parsed2 is not None
    assert parsed2["amount"] == 2000000.0
    assert parsed2["type"] == "income"
    assert parsed2["category_name"] == "Oylik"
    assert parsed2["account_name"] == "Uzcard"

    # Test case 3: Expense with plain number
    phrase3 = "Benzinga 100000 ketdi"
    parsed3 = parse_financial_voice_text(phrase3, mock_categories, mock_accounts)
    print(f"[+] Phrase 3: '{phrase3}' -> {parsed3}")
    assert parsed3 is not None
    assert parsed3["amount"] == 100000.0
    assert parsed3["type"] == "expense"
    assert parsed3["category_name"] == "Benzin"

    print("\n--- 5-BOSQICH UNIT TESTLARI MUVAFFAQIYATLI YAKUNLANDI ---")

if __name__ == "__main__":
    main()
