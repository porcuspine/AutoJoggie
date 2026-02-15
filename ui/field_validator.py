
class FieldValidator:
    @staticmethod
    def is_valid_decimal(chars:str) -> bool:
        if chars == "":
            return True
        if chars.count('.') > 1:
            return False
        return all(c in "0123456789." for c in chars) and chars.count('.') <= 1

    @staticmethod
    def is_valid_int(chars:str) -> bool:
        if chars == "":
            return True
        return all(c in "0123456789" for c in chars)
