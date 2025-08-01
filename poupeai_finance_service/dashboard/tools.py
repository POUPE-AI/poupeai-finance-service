def get_difference_in_percent(initial_balance, current_balance):
    if initial_balance == 0:
        return 100.0 if current_balance > 0 else -100.0
    else:
        difference = current_balance - initial_balance
        return (difference / abs(initial_balance)) * 100 if initial_balance != 0 else 0.0