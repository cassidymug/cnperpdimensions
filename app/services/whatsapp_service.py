"""
WhatsApp Integration Service

This service handles WhatsApp messaging for invoices and other business communications
using WhatsApp Business API or Twilio WhatsApp API.
"""

import requests
import json
from typing import Optional, Dict, Any
from io import BytesIO
import base64
from datetime import datetime

from app.models.app_setting import AppSetting
from sqlalchemy.orm import Session


class WhatsAppService:
    """WhatsApp messaging service for business communications"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, str]:
        """Load WhatsApp settings from database"""
        settings = {}
        whatsapp_settings = self.db.query(AppSetting).filter(
            AppSetting.key.in_([
                'whatsapp_enabled',
                'whatsapp_api_provider',  # 'twilio' or 'whatsapp_business'
                'whatsapp_number',
                'whatsapp_api_key',
                'whatsapp_api_secret',
                'twilio_account_sid',
                'twilio_auth_token',
                'twilio_whatsapp_number',
                'whatsapp_business_token',
                'whatsapp_business_phone_id'
            ])
        ).all()
        
        for setting in whatsapp_settings:
            settings[setting.key] = setting.value
        
        return settings
    
    def is_enabled(self) -> bool:
        """Check if WhatsApp is enabled and configured"""
        return (
            self.settings.get('whatsapp_enabled', 'false').lower() == 'true' and
            self.settings.get('whatsapp_api_provider') and
            self._is_provider_configured()
        )
    
    def _is_provider_configured(self) -> bool:
        """Check if the selected provider is properly configured"""
        provider = self.settings.get('whatsapp_api_provider')
        
        if provider == 'twilio':
            return all([
                self.settings.get('twilio_account_sid'),
                self.settings.get('twilio_auth_token'),
                self.settings.get('twilio_whatsapp_number')
            ])
        elif provider == 'whatsapp_business':
            return all([
                self.settings.get('whatsapp_business_token'),
                self.settings.get('whatsapp_business_phone_id')
            ])
        
        return False
    
    def send_invoice(
        self, 
        customer_phone: str, 
        invoice_data: Dict[str, Any], 
        pdf_buffer: BytesIO = None
    ) -> Dict[str, Any]:
        """Send invoice via WhatsApp"""
        
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'WhatsApp service is not enabled or configured'
            }
        
        # Format phone number
        formatted_phone = self._format_phone_number(customer_phone)
        if not formatted_phone:
            return {
                'success': False,
                'error': 'Invalid phone number format'
            }
        
        # Create message
        message = self._create_invoice_message(invoice_data)
        
        provider = self.settings.get('whatsapp_api_provider')
        
        try:
            if provider == 'twilio':
                result = self._send_via_twilio(formatted_phone, message, pdf_buffer)
            elif provider == 'whatsapp_business':
                result = self._send_via_whatsapp_business(formatted_phone, message, pdf_buffer)
            else:
                return {
                    'success': False,
                    'error': 'Invalid WhatsApp provider configured'
                }
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send WhatsApp message: {str(e)}'
            }
    
    def _format_phone_number(self, phone: str) -> Optional[str]:
        """Format phone number for WhatsApp (international format)"""
        if not phone:
            return None
        
        # Remove all non-digit characters
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Add country code if not present (assuming Botswana +267)
        if len(clean_phone) == 8 and clean_phone.startswith(('7', '2', '3')):
            return f"+267{clean_phone}"
        elif len(clean_phone) == 11 and clean_phone.startswith('267'):
            return f"+{clean_phone}"
        elif clean_phone.startswith('+'):
            return clean_phone
        else:
            # Try to detect other formats
            if len(clean_phone) >= 10:
                return f"+{clean_phone}"
        
        return None
    
    def _create_invoice_message(self, invoice_data: Dict[str, Any]) -> str:
        """Create formatted invoice message for WhatsApp"""
        company_name = self.settings.get('company_name', 'Your Company')
        currency_symbol = self.settings.get('currency_symbol', 'P')
        
        message = f"""🧾 *INVOICE FROM {company_name.upper()}*

📋 *Invoice Details:*
• Invoice No: {invoice_data['invoice_number']}
• Date: {invoice_data['date']}
• Due Date: {invoice_data['due_date']}

👤 *Bill To:*
{invoice_data['customer_name']}

💰 *Amount Summary:*
• Subtotal: {currency_symbol}{invoice_data['subtotal']:.2f}
• VAT: {currency_symbol}{invoice_data['vat_amount']:.2f}
• *Total: {currency_symbol}{invoice_data['total_amount']:.2f}*

📅 *Payment Terms:* {invoice_data['payment_terms']} days

Thank you for your business! 🙏

---
{company_name}
📞 {self.settings.get('company_phone', '')}
📧 {self.settings.get('company_email', '')}"""

        return message
    
    def _send_via_twilio(
        self, 
        to_number: str, 
        message: str, 
        pdf_buffer: BytesIO = None
    ) -> Dict[str, Any]:
        """Send message via Twilio WhatsApp API"""
        from twilio.rest import Client
        
        account_sid = self.settings.get('twilio_account_sid')
        auth_token = self.settings.get('twilio_auth_token')
        from_number = self.settings.get('twilio_whatsapp_number')
        
        client = Client(account_sid, auth_token)
        
        try:
            # Send text message
            message_obj = client.messages.create(
                body=message,
                from_=f"whatsapp:{from_number}",
                to=f"whatsapp:{to_number}"
            )
            
            result = {
                'success': True,
                'message_sid': message_obj.sid,
                'status': message_obj.status
            }
            
            # Send PDF if provided
            if pdf_buffer:
                # Upload PDF to a temporary URL or send as media
                # Note: Twilio requires a publicly accessible URL for media
                # In production, you'd upload to cloud storage first
                result['pdf_note'] = 'PDF attachment requires public URL setup'
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Twilio error: {str(e)}'
            }
    
    def _send_via_whatsapp_business(
        self, 
        to_number: str, 
        message: str, 
        pdf_buffer: BytesIO = None
    ) -> Dict[str, Any]:
        """Send message via WhatsApp Business API"""
        token = self.settings.get('whatsapp_business_token')
        phone_id = self.settings.get('whatsapp_business_phone_id')
        
        url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Remove + from phone number for WhatsApp Business API
        clean_number = to_number.replace('+', '')
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': clean_number,
            'type': 'text',
            'text': {
                'body': message
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result_data = response.json()
            
            return {
                'success': True,
                'message_id': result_data.get('messages', [{}])[0].get('id'),
                'status': 'sent'
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'WhatsApp Business API error: {str(e)}'
            }
    
    def send_custom_message(
        self, 
        phone_number: str, 
        message: str
    ) -> Dict[str, Any]:
        """Send custom WhatsApp message"""
        
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'WhatsApp service is not enabled or configured'
            }
        
        formatted_phone = self._format_phone_number(phone_number)
        if not formatted_phone:
            return {
                'success': False,
                'error': 'Invalid phone number format'
            }
        
        provider = self.settings.get('whatsapp_api_provider')
        
        try:
            if provider == 'twilio':
                return self._send_via_twilio(formatted_phone, message)
            elif provider == 'whatsapp_business':
                return self._send_via_whatsapp_business(formatted_phone, message)
            else:
                return {
                    'success': False,
                    'error': 'Invalid WhatsApp provider configured'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send WhatsApp message: {str(e)}'
            }
    
    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Get status of a sent message"""
        provider = self.settings.get('whatsapp_api_provider')
        
        if provider == 'twilio':
            return self._get_twilio_message_status(message_id)
        elif provider == 'whatsapp_business':
            return self._get_whatsapp_business_status(message_id)
        else:
            return {
                'success': False,
                'error': 'Invalid provider'
            }
    
    def _get_twilio_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get message status from Twilio"""
        try:
            from twilio.rest import Client
            
            account_sid = self.settings.get('twilio_account_sid')
            auth_token = self.settings.get('twilio_auth_token')
            
            client = Client(account_sid, auth_token)
            message = client.messages(message_sid).fetch()
            
            return {
                'success': True,
                'status': message.status,
                'error_code': message.error_code,
                'error_message': message.error_message
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_whatsapp_business_status(self, message_id: str) -> Dict[str, Any]:
        """Get message status from WhatsApp Business API"""
        # WhatsApp Business API doesn't provide direct message status lookup
        # Status updates come via webhooks
        return {
            'success': True,
            'status': 'sent',
            'note': 'Status tracking requires webhook setup'
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test WhatsApp API connection"""
        if not self.is_enabled():
            return {
                'success': False,
                'error': 'WhatsApp service is not enabled or configured'
            }
        
        provider = self.settings.get('whatsapp_api_provider')
        
        if provider == 'twilio':
            return self._test_twilio_connection()
        elif provider == 'whatsapp_business':
            return self._test_whatsapp_business_connection()
        else:
            return {
                'success': False,
                'error': 'Invalid provider'
            }
    
    def _test_twilio_connection(self) -> Dict[str, Any]:
        """Test Twilio connection"""
        try:
            from twilio.rest import Client
            
            account_sid = self.settings.get('twilio_account_sid')
            auth_token = self.settings.get('twilio_auth_token')
            
            client = Client(account_sid, auth_token)
            account = client.api.accounts(account_sid).fetch()
            
            return {
                'success': True,
                'provider': 'twilio',
                'account_sid': account.sid,
                'status': account.status
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Twilio connection failed: {str(e)}'
            }
    
    def _test_whatsapp_business_connection(self) -> Dict[str, Any]:
        """Test WhatsApp Business API connection"""
        try:
            token = self.settings.get('whatsapp_business_token')
            phone_id = self.settings.get('whatsapp_business_phone_id')
            
            url = f"https://graph.facebook.com/v18.0/{phone_id}"
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'success': True,
                'provider': 'whatsapp_business',
                'phone_id': phone_id,
                'verified_name': data.get('verified_name'),
                'display_phone_number': data.get('display_phone_number')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'WhatsApp Business API connection failed: {str(e)}'
            }


def get_whatsapp_service(db: Session) -> WhatsAppService:
    """Factory function to get WhatsAppService instance"""
    return WhatsAppService(db)
