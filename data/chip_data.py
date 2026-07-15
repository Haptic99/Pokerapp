# data/chip_data.py

class ChipData:
    """Stores values for poker chips and their equivalent in CHF."""
    
    # Chips and their values (in chips)
    CHIPS = {
        "chip_25.png": 25,
        "chip_50.png": 50,
        "chip_100.png": 100,
        "chip_500.png": 500,
        "chip_1000.png": 1000,
        "chip_5000.png": 5000,
        "chip_10000.png": 10000
    }
    
    # CHF values (default ratio: 1 CHF = 100 chips)
    chf_values = {
        "chip_25.png": 0.25,
        "chip_50.png": 0.50,
        "chip_100.png": 1.00,
        "chip_500.png": 5.00,
        "chip_1000.png": 10.00,
        "chip_5000.png": 50.00,
        "chip_10000.png": 100.00
    }

    # Sets a new CHF value for a chip and updates all other chips proportionally
    @classmethod
    def set_chf_value(cls, chip_filename, new_chf_value):
        if chip_filename not in cls.CHIPS:
            return False
            
        # Calculate ratio
        chip_value = cls.CHIPS[chip_filename]
        ratio = new_chf_value / chip_value
        
        # Update all chips based on the new ratio
        for chip, value in cls.CHIPS.items():
            cls.chf_values[chip] = value * ratio
            
        return True
