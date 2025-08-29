import streamlit as st
import random
from collections import Counter

# -----------------------------
# Utility functions
# -----------------------------

suits = ["♠", "♥", "♣", "♦"]
ranks = {1: "A", 11: "J", 12: "Q", 13: "K"}
for i in range(2, 11):
    ranks[i] = str(i)

def card_name(value, suit):
    return f"{ranks[value]}{suit}"

def init_shoe(decks=8):
    shoe = []
    for _ in range(decks):
        for v in range(1, 14):
            for s in suits:
                shoe.append((v, s))
    random.shuffle(shoe)
    return shoe

def calc_probabilities(shoe, payouts, tie_rule):
    wins = Counter()
    total = 0
    n = len(shoe)
    for i in range(n):
        for j in range(n):
            if i == j: 
                continue
            d = shoe[i]
            t = shoe[j]
            total += 1
            if d[0] > t[0]:
                wins["Dragon"] += 1
            elif t[0] > d[0]:
                wins["Tiger"] += 1
            else:
                if d[1] == t[1]:
                    wins["Tie"] += 1
                else:
                    # rank tie, suit decides
                    if suits.index(d[1]) < suits.index(t[1]):
                        wins["Dragon"] += 1
                    else:
                        wins["Tiger"] += 1
    probs = {k: wins[k] / total for k in ["Dragon", "Tiger", "Tie"]}
    probs["Pair"] = 0
    for i in range(n):
        for j in range(i+1, n):
            if shoe[i][0] == shoe[j][0]:
                probs["Pair"] += 2 / (n * (n-1))
    # EVs
    evs = {}
    for bet in ["Dragon", "Tiger", "Tie", "Pair"]:
        if bet == "Dragon":
            win_prob = probs["Dragon"]
            lose_prob = probs["Tiger"]
            tie_prob = probs["Tie"]
            if tie_rule == "push":
                evs[bet] = win_prob * payouts["Dragon"] - lose_prob
            else:
                evs[bet] = win_prob * payouts["Dragon"] - (lose_prob + tie_prob)
        elif bet == "Tiger":
            win_prob = probs["Tiger"]
            lose_prob = probs["Dragon"]
            tie_prob = probs["Tie"]
            if tie_rule == "push":
                evs[bet] = win_prob * payouts["Tiger"] - lose_prob
            else:
                evs[bet] = win_prob * payouts["Tiger"] - (lose_prob + tie_prob)
        elif bet == "Tie":
            evs[bet] = probs["Tie"] * payouts["Tie"] - (1 - probs["Tie"])
        elif bet == "Pair":
            evs[bet] = probs["Pair"] * payouts["Pair"] - (1 - probs["Pair"])
    return probs, evs

# -----------------------------
# Streamlit App
# -----------------------------

st.title("🐉🐯 Dragon–Tiger Tracker")

# Session state init
if "shoe" not in st.session_state:
    st.session_state.decks = 8
    st.session_state.shoe = init_shoe(st.session_state.decks)
    st.session_state.bankroll = 100
    st.session_state.history = []
    st.session_state.payouts = {"Dragon": 1, "Tiger": 1, "Tie": 11, "Pair": 11}
    st.session_state.tie_rule = "lose"

# Config panel
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.decks = st.number_input("Decks", 1, 20, st.session_state.decks)
    if st.button("Reset Shoe"):
        st.session_state.shoe = init_shoe(st.session_state.decks)
        st.session_state.history = []
    st.session_state.bankroll = st.number_input("Bankroll", 1, 10000, st.session_state.bankroll)
    st.session_state.payouts["Dragon"] = st.number_input("Dragon Payout", 1, 10, 1)
    st.session_state.payouts["Tiger"] = st.number_input("Tiger Payout", 1, 10, 1)
    st.session_state.payouts["Tie"] = st.number_input("Tie Payout", 1, 50, 11)
    st.session_state.payouts["Pair"] = st.number_input("Pair Payout", 1, 50, 11)
    st.session_state.tie_rule = st.radio("Tie Rule", ["lose", "push"], index=0)

# Probabilities
probs, evs = calc_probabilities(st.session_state.shoe, st.session_state.payouts, st.session_state.tie_rule)
st.subheader("📊 Current Probabilities")
st.write({k: f"{100*v:.2f}%" for k, v in probs.items()})
st.subheader("💹 Expected Values (per unit bet)")
st.write(evs)

# Enter round
st.subheader("🎴 Enter Round Results")
col1, col2 = st.columns(2)
with col1:
    d_rank = st.selectbox("Dragon Rank", list(ranks.values()))
    d_suit = st.selectbox("Dragon Suit", suits)
with col2:
    t_rank = st.selectbox("Tiger Rank", list(ranks.values()))
    t_suit = st.selectbox("Tiger Suit", suits)

bet_side = st.selectbox("Your Bet", ["None", "Dragon", "Tiger", "Tie", "Pair"])
bet_amount = st.number_input("Bet Amount", 0, 1000, 0)

if st.button("Submit Round"):
    # map back ranks
    inv_ranks = {v: k for k, v in ranks.items()}
    d_card = (inv_ranks[d_rank], d_suit)
    t_card = (inv_ranks[t_rank], t_suit)
    # remove from shoe
    if d_card in st.session_state.shoe:
        st.session_state.shoe.remove(d_card)
    if t_card in st.session_state.shoe:
        st.session_state.shoe.remove(t_card)
    # outcome
    if d_card[0] > t_card[0]:
        result = "Dragon"
    elif t_card[0] > d_card[0]:
        result = "Tiger"
    else:
        if d_card[1] == t_card[1]:
            result = "Tie"
        else:
            result = "Dragon" if suits.index(d_card[1]) < suits.index(t_card[1]) else "Tiger"
    # bankroll update
    change = 0
    if bet_side != "None" and bet_amount > 0:
        if bet_side == result:
            change = bet_amount * st.session_state.payouts[bet_side]
        elif bet_side in ["Dragon", "Tiger"] and result == "Tie":
            if st.session_state.tie_rule == "push":
                change = 0
            else:
                change = -bet_amount
        else:
            change = -bet_amount
        st.session_state.bankroll += change
    # log
    st.session_state.history.append({
        "Dragon": card_name(*d_card),
        "Tiger": card_name(*t_card),
        "Result": result,
        "Bet": f"{bet_side} {bet_amount}",
        "Change": change,
        "Bankroll": st.session_state.bankroll
    })

# History
st.subheader("📜 History")
if st.session_state.history:
    st.table(st.session_state.history)
else:
    st.write("No rounds yet.")
