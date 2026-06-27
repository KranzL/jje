from decimal import Decimal


def compute_subtotal(line_items):
    subtotal = Decimal("0")
    for item in line_items:
        subtotal += Decimal(item["unit_price"]) * item["quantity"]
    return subtotal


def apply_tax(subtotal, tax_rate):
    return subtotal + (subtotal * Decimal(tax_rate))


def invoice_total(line_items, tax_rate):
    subtotal = compute_subtotal(line_items)
    return apply_tax(subtotal, tax_rate)
