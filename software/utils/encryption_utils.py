# software/utils/encryption_utils.py
"""
Utilidades para cifrar/descifrar datos sensibles
"""
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
import base64
import os

class EncryptionManager:
    """
    Gestor de cifrado para datos sensibles como correos electrónicos
    """
    
    @staticmethod
    def get_encryption_key():
        """
        Obtiene la clave de cifrado desde settings
        Si no existe, genera una nueva (solo para desarrollo)
        """
        if hasattr(settings, 'ENCRYPTION_KEY'):
            return settings.ENCRYPTION_KEY.encode()
        
        # ADVERTENCIA: En producción, la clave debe estar en variables de entorno
        # Esta es solo para desarrollo
        key = Fernet.generate_key()
        print(f"ADVERTENCIA: Genera una clave y agrégala a settings.py: ENCRYPTION_KEY = '{key.decode()}'")
        return key
    
    @staticmethod
    def encrypt_data(data):
        """
        Cifra datos genéricos (como correos o nombres de usuario)
        Args:
            data (str): Dato en texto plano
        Returns:
            str: Dato cifrado en base64
        """
        if not data:
            return None
            
        try:
            key = EncryptionManager.get_encryption_key()
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            print(f"Error al cifrar datos: {e}")
            return None
    


    @staticmethod
    def encrypt_email(email):
        return EncryptionManager.encrypt_data(email)
    
    @staticmethod
    def decrypt_data(encrypted_data):
        """
        Descifra datos genéricos (como correos o nombres de usuario)
        Args:
            encrypted_data (str): Dato cifrado en base64
        Returns:
            str: Dato en texto plano
        """
        if not encrypted_data:
            return None
            
        try:
            key = EncryptionManager.get_encryption_key()
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            print(f"Error al descifrar datos: {e}")
            return None
    
    @staticmethod
    def decrypt_email(encrypted_email):
        return EncryptionManager.decrypt_data(encrypted_email)


class PasswordManager:
    """
    Gestor de contraseñas usando el sistema de hashing de Django
    """
    
    @staticmethod
    def hash_password(plain_password):
        """
        Hashea una contraseña usando el sistema de Django
        Args:
            plain_password (str): Contraseña en texto plano
        Returns:
            str: Hash de la contraseña
        """
        if not plain_password:
            return None
        return make_password(plain_password)
    
    @staticmethod
    def verify_password(plain_password, hashed_password):
        """
        Verifica si una contraseña coincide con su hash
        Args:
            plain_password (str): Contraseña en texto plano
            hashed_password (str): Hash de la contraseña
        Returns:
            bool: True si coinciden, False si no
        """
        return check_password(plain_password, hashed_password)