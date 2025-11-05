"""
Weight-based barcode utilities for meat, fruits, and vegetables
Barcode format: [Type:2][Product:5][Weight:5][Check:1] = 13 digits total
Compatible with EAN-13 format
"""
from typing import Dict, Optional, Tuple
from decimal import Decimal

# Barcode type prefixes
BARCODE_TYPES = {
    '20': 'meat',
    '21': 'fruits',
    '22': 'vegetables',
    '23': 'dairy',  # Future expansion
    '24': 'bakery',  # Future expansion
}

CATEGORY_PREFIXES = {
    'meat': '20',
    'fruits': '21',
    'vegetables': '22',
    'dairy': '23',
    'bakery': '24',
}


def calculate_checksum(barcode_without_check: str) -> str:
    """
    Calculate modulo-10 checksum for barcode (EAN-13 compatible)
    
    Args:
        barcode_without_check: 12-digit barcode without checksum
        
    Returns:
        Single check digit as string
    """
    if len(barcode_without_check) != 12:
        raise ValueError(f"Barcode must be 12 digits, got {len(barcode_without_check)}")
    
    # EAN-13 checksum: multiply odd positions by 1, even by 3
    odd_sum = sum(int(barcode_without_check[i]) for i in range(0, 12, 2))
    even_sum = sum(int(barcode_without_check[i]) for i in range(1, 12, 2))
    
    total = odd_sum + (even_sum * 3)
    check_digit = (10 - (total % 10)) % 10
    
    return str(check_digit)


def generate_weight_barcode(
    category: str,
    product_code: str,
    weight_grams: float,
    include_check: bool = True
) -> str:
    """
    Generate a weight-based barcode
    
    Args:
        category: Product category ('meat', 'fruits', 'vegetables')
        product_code: 5-digit product code (e.g., '12345')
        weight_grams: Weight in grams (max 99999g = 99.999kg)
        include_check: Whether to include checksum digit
        
    Returns:
        13-digit barcode string (or 12 without check)
        
    Example:
        >>> generate_weight_barcode('meat', '12345', 1500.0)
        '2012345015007'  # 20-12345-01500-7
        # Type 20 (meat), Product 12345, 1500g (1.5kg), Check digit 7
    """
    # Validate inputs
    if category not in CATEGORY_PREFIXES:
        raise ValueError(f"Invalid category: {category}. Must be one of {list(CATEGORY_PREFIXES.keys())}")
    
    if not product_code.isdigit() or len(product_code) != 5:
        raise ValueError(f"Product code must be 5 digits, got: {product_code}")
    
    if weight_grams < 0 or weight_grams > 99999:
        raise ValueError(f"Weight must be between 0 and 99999 grams, got: {weight_grams}")
    
    # Build barcode
    type_prefix = CATEGORY_PREFIXES[category]
    weight_str = f"{int(weight_grams):05d}"  # 5 digits, zero-padded
    
    barcode_12 = f"{type_prefix}{product_code}{weight_str}"
    
    if include_check:
        check_digit = calculate_checksum(barcode_12)
        return f"{barcode_12}{check_digit}"
    
    return barcode_12


def parse_weight_barcode(barcode: str) -> Optional[Dict]:
    """
    Parse a weight-based barcode into its components
    
    Args:
        barcode: 13-digit barcode string (with or without dashes)
        
    Returns:
        Dictionary with parsed components or None if invalid
        {
            'type_code': '20',
            'category': 'meat',
            'product_code': '12345',
            'weight_grams': 1500,
            'weight_kg': 1.5,
            'checksum': '7',
            'is_valid': True
        }
    """
    # Remove any formatting (dashes, spaces)
    clean_barcode = barcode.replace('-', '').replace(' ', '').strip()
    
    # Validate length
    if len(clean_barcode) not in [12, 13]:
        return None
    
    # Extract components
    type_code = clean_barcode[0:2]
    product_code = clean_barcode[2:7]
    weight_str = clean_barcode[7:12]
    checksum = clean_barcode[12] if len(clean_barcode) == 13 else None
    
    # Validate type code
    if type_code not in BARCODE_TYPES:
        return None
    
    # Validate numeric parts
    if not product_code.isdigit() or not weight_str.isdigit():
        return None
    
    # Validate checksum if present
    is_valid = True
    if checksum:
        expected_check = calculate_checksum(clean_barcode[:12])
        is_valid = (checksum == expected_check)
    
    weight_grams = int(weight_str)
    
    return {
        'type_code': type_code,
        'category': BARCODE_TYPES[type_code],
        'product_code': product_code,
        'weight_grams': weight_grams,
        'weight_kg': weight_grams / 1000.0,
        'checksum': checksum,
        'is_valid': is_valid,
        'barcode': clean_barcode
    }


def calculate_price(weight_grams: float, price_per_kg: Decimal, tare_weight: float = 0) -> Decimal:
    """
    Calculate price for weight-based product
    
    Args:
        weight_grams: Gross weight in grams (including container)
        price_per_kg: Price per kilogram
        tare_weight: Container/packaging weight in grams to subtract
        
    Returns:
        Total price as Decimal
    """
    net_weight_grams = max(0, weight_grams - tare_weight)
    net_weight_kg = Decimal(str(net_weight_grams / 1000.0))
    
    return (net_weight_kg * price_per_kg).quantize(Decimal('0.01'))


def format_barcode_display(barcode: str) -> str:
    """
    Format barcode for display with dashes
    
    Args:
        barcode: 13-digit barcode
        
    Returns:
        Formatted string like "20-12345-01500-7"
    """
    clean = barcode.replace('-', '').replace(' ', '')
    if len(clean) == 13:
        return f"{clean[0:2]}-{clean[2:7]}-{clean[7:12]}-{clean[12]}"
    elif len(clean) == 12:
        return f"{clean[0:2]}-{clean[2:7]}-{clean[7:12]}"
    return barcode


def validate_weight_range(weight_grams: float, min_weight: Optional[float], max_weight: Optional[float]) -> Tuple[bool, str]:
    """
    Validate if weight is within acceptable range
    
    Returns:
        (is_valid, error_message)
    """
    if min_weight and weight_grams < min_weight:
        return False, f"Weight {weight_grams}g is below minimum {min_weight}g"
    
    if max_weight and weight_grams > max_weight:
        return False, f"Weight {weight_grams}g exceeds maximum {max_weight}g"
    
    return True, ""


# JavaScript-compatible version for frontend
def generate_javascript_barcode_parser() -> str:
    """
    Generate JavaScript code for barcode parsing in frontend
    """
    return """
// Weight-based barcode parser for POS
const BarcodeParser = {
    TYPES: {
        '20': 'Meat',
        '21': 'Fruits',
        '22': 'Vegetables',
        '23': 'Dairy',
        '24': 'Bakery'
    },
    
    calculateChecksum(barcode12) {
        if (barcode12.length !== 12) return null;
        
        let oddSum = 0, evenSum = 0;
        for (let i = 0; i < 12; i++) {
            if (i % 2 === 0) oddSum += parseInt(barcode12[i]);
            else evenSum += parseInt(barcode12[i]);
        }
        
        const total = oddSum + (evenSum * 3);
        return ((10 - (total % 10)) % 10).toString();
    },
    
    parse(barcode) {
        // Remove formatting
        const clean = barcode.replace(/[-\\s]/g, '');
        
        if (clean.length !== 13 && clean.length !== 12) return null;
        
        const typeCode = clean.substring(0, 2);
        const productCode = clean.substring(2, 7);
        const weightStr = clean.substring(7, 12);
        const checksum = clean.length === 13 ? clean[12] : null;
        
        if (!this.TYPES[typeCode]) return null;
        
        const weightGrams = parseInt(weightStr);
        let isValid = true;
        
        if (checksum) {
            const expected = this.calculateChecksum(clean.substring(0, 12));
            isValid = (checksum === expected);
        }
        
        return {
            typeCode: typeCode,
            category: this.TYPES[typeCode],
            productCode: productCode,
            weightGrams: weightGrams,
            weightKg: weightGrams / 1000,
            checksum: checksum,
            isValid: isValid,
            barcode: clean
        };
    },
    
    isWeightBarcode(barcode) {
        const clean = barcode.replace(/[-\\s]/g, '');
        return clean.length >= 12 && this.TYPES.hasOwnProperty(clean.substring(0, 2));
    },
    
    calculatePrice(weightGrams, pricePerKg, tareWeight = 0) {
        const netWeight = Math.max(0, weightGrams - tareWeight);
        const netWeightKg = netWeight / 1000;
        return (netWeightKg * pricePerKg).toFixed(2);
    },
    
    format(barcode) {
        const clean = barcode.replace(/[-\\s]/g, '');
        if (clean.length === 13) {
            return `${clean.substring(0,2)}-${clean.substring(2,7)}-${clean.substring(7,12)}-${clean[12]}`;
        }
        return barcode;
    }
};
"""


if __name__ == "__main__":
    # Test examples
    print("🧪 Weight Barcode System Tests\n")
    
    # Test 1: Generate barcode for 1.5kg of meat
    barcode1 = generate_weight_barcode('meat', '12345', 1500.0)
    print(f"✓ Meat barcode (1.5kg): {format_barcode_display(barcode1)}")
    
    # Test 2: Parse the barcode
    parsed = parse_weight_barcode(barcode1)
    print(f"  Parsed: {parsed['category']}, Product {parsed['product_code']}, {parsed['weight_kg']}kg")
    print(f"  Valid: {parsed['is_valid']}\n")
    
    # Test 3: Calculate price
    price = calculate_price(1500, Decimal('25.50'), tare_weight=50)
    print(f"✓ Price calculation: 1.5kg @ R25.50/kg (50g tare) = R{price}\n")
    
    # Test 4: Generate barcodes for different categories
    test_cases = [
        ('meat', '00001', 2500, 'Beef Steak'),
        ('fruits', '00123', 850, 'Apples'),
        ('vegetables', '00456', 1200, 'Tomatoes'),
    ]
    
    print("📊 Sample Barcodes:\n")
    for category, code, weight, name in test_cases:
        bc = generate_weight_barcode(category, code, weight)
        parsed = parse_weight_barcode(bc)
        print(f"{name:15} {format_barcode_display(bc):20} ({parsed['weight_kg']}kg {parsed['category']})")
