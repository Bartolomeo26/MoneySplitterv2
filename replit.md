# Where is my money? - Aplikacja do rozliczeń grupowych

## Przegląd
Aplikacja webowa do rozliczeń grupowych (split bills) zbudowana w FastAPI + HTMX/Tailwind CSS. Umożliwia łatwe zarządzanie wydatkami grupowymi i automatyczne wyliczanie, kto komu ile jest winien.

## Funkcjonalności MVP

### Zaimplementowane funkcje:
- ✅ Generowanie unikalnych sesji rozliczeń dostępnych przez link (UUID)
- ✅ Dodawanie i zarządzanie uczestnikami sesji
- ✅ Dodawanie wydatków z wyborem płatnika i beneficjentów
- ✅ Automatyczny równy podział kwoty między beneficjentów
- ✅ Automatyczne wyliczanie sald uczestników
- ✅ Optymalizacja płatności (algorytm minimalizujący liczbę przelewów)
- ✅ Tryb tylko do odczytu (read-only mode)
- ✅ Eksport danych do CSV i PDF
- ✅ Responsywny interfejs z HTMX i Tailwind CSS
- ✅ Walidacja danych (kwota > 0, płatnik jako uczestnik, co najmniej jeden beneficjent)
- ✅ Obliczenia w groszach (amount_minor) z deterministycznym zaokrąglaniem

## Struktura projektu

```
.
├── main.py                          # Główna aplikacja FastAPI z routami
├── models.py                        # Modele danych (Session, Participant, Expense, Settlement)
├── storage.py                       # In-memory storage dla sesji
├── settlement.py                    # Logika obliczania sald i optymalizacji płatności
├── utils.py                         # Funkcje pomocnicze (formatowanie kwot, parsowanie)
├── templates/
│   ├── base.html                   # Szablon bazowy
│   ├── home.html                   # Strona główna (tworzenie sesji)
│   ├── session.html                # Widok sesji rozliczeń
│   └── partials/
│       ├── participants_list.html  # Partial dla listy uczestników
│       └── expenses_and_settlement.html  # Partial dla wydatków i rozliczenia
├── .gitignore                      # Git ignore dla Pythona
└── replit.md                       # Dokumentacja projektu
```

## Technologie

### Backend:
- **FastAPI** - framework webowy
- **Pydantic** - walidacja danych
- **SQLite/In-memory** - przechowywanie sesji (dane w pamięci)
- **ReportLab** - generowanie PDF
- **Uvicorn** - serwer ASGI

### Frontend:
- **HTMX** - interaktywność bez JavaScript
- **Tailwind CSS** - stylowanie (CDN dla rozwoju)
- **Jinja2** - templating HTML

## Jak uruchomić

Aplikacja uruchamia się automatycznie przez workflow "web":
```bash
python main.py
```

Serwer dostępny jest na `http://0.0.0.0:5000`

## Model danych

### Session
- `id`: UUID sesji
- `name`: nazwa sesji
- `created_at`: data utworzenia
- `read_only`: flaga trybu tylko do odczytu
- `participants`: lista uczestników
- `expenses`: lista wydatków

### Participant
- `id`: UUID uczestnika
- `name`: imię/pseudonim

### Expense
- `id`: UUID wydatku
- `title`: tytuł wydatku
- `amount_minor`: kwota w groszach (int)
- `date`: data wydatku
- `payer_id`: ID płatnika
- `beneficiary_ids`: lista ID beneficjentów

### Settlement (generowane)
- `balances`: salda uczestników
- `payments`: lista płatności do wykonania

## Algorytmy

### Obliczanie sald
1. Każdy beneficjent otrzymuje równą część wydatku
2. Zaokrąglanie deterministyczne (pierwsi beneficjenci dostają nadwyżkę groszy)
3. Płatnik otrzymuje kredyt za całą zapłaconą kwotę
4. Salda sortowane malejąco

### Optymalizacja płatności
Algorytm greedy minimalizujący liczbę przelewów:
1. Sortowanie dłużników (malejąco po kwocie długu)
2. Sortowanie wierzycieli (malejąco po kwocie należności)
3. Dopasowywanie największych długów z największymi należnościami
4. Rezultat: minimalna liczba przelewów

## Walidacje

- Kwota > 0
- Płatnik musi być uczestnikiem sesji
- Co najmniej jeden beneficjent
- Wszystkie kwoty w groszach (int)
- Nazwy nie mogą być puste

## Eksport danych

### CSV
- Nagłówki z nazwą sesji i datą
- Lista uczestników
- Wszystkie wydatki
- Salda końcowe
- Lista płatności

### PDF
- Sformatowany dokument A4
- Tabele z wydatkami, saldami i płatnościami
- Kolorowanie i stylowanie
- Obsługa polskich znaków

## Stan projektu

**Data ostatniej aktualizacji**: 2025-11-15

### Aktualny status:
- MVP w pełni zaimplementowane
- Wszystkie funkcje działają poprawnie
- Aplikacja gotowa do użycia

### Możliwe rozszerzenia (poza MVP):
- Edycja i usuwanie wydatków/uczestników
- Persystentna baza danych (PostgreSQL/SQLite)
- Nierówny podział wydatków
- Kategorie wydatków
- Powiadomienia email
- Multi-currency support
- Autentykacja i autoryzacja
- Historia zmian
