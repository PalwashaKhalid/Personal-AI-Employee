"""
Odoo MCP Server - Accounting Integration

Integrates with Odoo Community Edition via JSON-RPC API.
Provides accounting functionality for the AI Employee.

Gold tier requirement for business accounting.

Setup:
1. Install Odoo Community Edition (local or cloud)
2. Get Odoo URL, database, username, and password
3. Configure in .env file

Usage:
    python odoo_mcp_server.py --url http://localhost:8069 --db mydb --user admin

Environment Variables:
    ODOO_URL: Odoo server URL
    ODOO_DB: Database name
    ODOO_USERNAME: Odoo username
    ODOO_PASSWORD: Odoo password
"""

import os
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging


class OdooMCP:
    """
    Odoo MCP Server for accounting integration.
    
    Uses Odoo's external JSON-RPC API (Odoo 19+).
    """
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        
        self.session = requests.Session()
        self.uid = None  # User ID after authentication
        
        # Set up logging
        self.logs_dir = Path.home() / '.ai_employee' / 'logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()
        
        # Authenticate
        self._authenticate()
    
    def _setup_logging(self) -> None:
        """Configure logging."""
        log_file = self.logs_dir / f'odoo_mcp_{datetime.now().strftime("%Y-%m-%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('OdooMCP')
    
    def _authenticate(self) -> None:
        """Authenticate with Odoo."""
        try:
            # Odoo 19+ uses /web/session/authenticate
            auth_url = f'{self.url}/web/session/authenticate'
            
            payload = {
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': self.db,
                    'login': self.username,
                    'password': self.password,
                    'context': {}
                },
                'id': 1
            }
            
            response = self.session.post(auth_url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('result'):
                self.uid = result['result'].get('uid')
                self.session_id = result['result'].get('session_id', '')
                
                # Set session cookie
                if self.session_id:
                    self.session.cookies.set('session_id', self.session_id)
                
                self.logger.info(f'Authenticated as user {self.uid}')
            else:
                self.logger.error('Authentication failed')
                raise Exception('Odoo authentication failed')
                
        except Exception as e:
            self.logger.error(f'Authentication error: {e}')
            raise
    
    def _rpc_call(self, model: str, method: str, args: List = None,
                  kwargs: Dict = None) -> Any:
        """
        Make JSON-RPC call to Odoo.
        
        Args:
            model: Odoo model name
            method: Method to call
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Method result
        """
        if not self.uid:
            raise Exception('Not authenticated')
        
        rpc_url = f'{self.url}/web/dataset/call'
        
        payload = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'model': model,
                'method': method,
                'args': args or [],
                'kwargs': kwargs or {}
            },
            'id': datetime.now().timestamp()
        }
        
        try:
            response = self.session.post(rpc_url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                error = result['error']
                self.logger.error(f'RPC error: {error.get("message", "Unknown")}')
                raise Exception(f'Odoo RPC error: {error}')
            
            return result.get('result', {}).get('result')
            
        except Exception as e:
            self.logger.error(f'RPC call error: {e}')
            raise
    
    # === Invoice Methods ===
    
    def create_invoice(self, partner_id: int, invoice_type: str = 'out_invoice',
                       lines: List[Dict] = None, **kwargs) -> int:
        """
        Create a customer invoice.
        
        Args:
            partner_id: Customer partner ID
            invoice_type: 'out_invoice' (customer) or 'in_invoice' (vendor)
            lines: Invoice line items [{'product_id': 1, 'quantity': 1, 'price_unit': 100}]
            **kwargs: Additional invoice fields
            
        Returns:
            Invoice ID
        """
        invoice_vals = {
            'move_type': invoice_type,
            'partner_id': partner_id,
            'invoice_date': kwargs.get('invoice_date', datetime.now().strftime('%Y-%m-%d')),
            'invoice_line_ids': []
        }
        
        # Add line items
        if lines:
            for line in lines:
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id': line.get('product_id'),
                    'quantity': line.get('quantity', 1),
                    'price_unit': line.get('price_unit', 0),
                    'name': line.get('name', '')
                }))
        
        invoice_id = self._rpc_call('account.move', 'create', [invoice_vals])
        self.logger.info(f'Created invoice {invoice_id}')
        return invoice_id
    
    def get_invoice(self, invoice_id: int) -> Optional[Dict]:
        """Get invoice details."""
        result = self._rpc_call(
            'account.move', 
            'search_read',
            [[['id', '=', invoice_id]]],
            {'fields': ['id', 'name', 'partner_id', 'amount_total', 'state', 'invoice_date']}
        )
        return result[0] if result else None
    
    def confirm_invoice(self, invoice_id: int) -> bool:
        """Confirm/post an invoice."""
        self._rpc_call('account.move', 'action_post', [[invoice_id]])
        self.logger.info(f'Confirmed invoice {invoice_id}')
        return True
    
    def get_invoices(self, state: str = 'draft', limit: int = 10) -> List[Dict]:
        """Get list of invoices."""
        domain = []
        if state:
            domain.append(['state', '=', state])
        
        return self._rpc_call(
            'account.move',
            'search_read',
            [domain],
            {
                'fields': ['id', 'name', 'partner_id', 'amount_total', 'state', 'invoice_date'],
                'limit': limit
            }
        )
    
    # === Payment Methods ===
    
    def register_payment(self, invoice_id: int, amount: float, 
                         payment_method: str = 'manual',
                         payment_date: str = None) -> int:
        """
        Register payment for an invoice.
        
        Args:
            invoice_id: Invoice ID
            amount: Payment amount
            payment_method: Payment method
            payment_date: Payment date
            
        Returns:
            Payment ID
        """
        wizard_vals = {
            'journal_id': 1,  # Default bank journal
            'payment_method_id': 1,  # Manual
            'amount': amount,
            'payment_date': payment_date or datetime.now().strftime('%Y-%m-%d')
        }
        
        # Create payment wizard
        wizard_id = self._rpc_call(
            'account.payment.register',
            'create',
            [wizard_vals]
        )
        
        # Create payment
        payment_result = self._rpc_call(
            'account.payment.register',
            'create_payments',
            [[wizard_id]]
        )
        
        self.logger.info(f'Registered payment {payment_result}')
        return payment_result
    
    # === Partner (Customer/Vendor) Methods ===
    
    def create_partner(self, name: str, partner_type: str = 'customer',
                       **kwargs) -> int:
        """
        Create a partner (customer/vendor).
        
        Args:
            name: Partner name
            partner_type: 'customer' or 'vendor'
            **kwargs: Additional fields (email, phone, etc.)
            
        Returns:
            Partner ID
        """
        partner_vals = {
            'name': name,
            'customer_rank': 1 if partner_type == 'customer' else 0,
            'supplier_rank': 1 if partner_type == 'vendor' else 0,
        }
        
        if 'email' in kwargs:
            partner_vals['email'] = kwargs['email']
        if 'phone' in kwargs:
            partner_vals['phone'] = kwargs['phone']
        
        partner_id = self._rpc_call('res.partner', 'create', [partner_vals])
        self.logger.info(f'Created partner {partner_id}')
        return partner_id
    
    def search_partner(self, name: str) -> List[Dict]:
        """Search for partners by name."""
        return self._rpc_call(
            'res.partner',
            'search_read',
            [[['name', 'ilike', name]]],
            {'fields': ['id', 'name', 'email', 'phone']}
        )
    
    # === Product Methods ===
    
    def create_product(self, name: str, product_type: str = 'service',
                       list_price: float = 0.0, **kwargs) -> int:
        """
        Create a product.
        
        Args:
            name: Product name
            product_type: 'service' or 'product'
            list_price: Sale price
            **kwargs: Additional fields
            
        Returns:
            Product ID
        """
        product_vals = {
            'name': name,
            'type': 'consu' if product_type == 'product' else 'service',
            'list_price': list_price,
            'detailed_type': 'product_consu' if product_type == 'product' else 'product_service'
        }
        
        if 'cost' in kwargs:
            product_vals['standard_price'] = kwargs['cost']
        
        product_id = self._rpc_call('product.template', 'create', [product_vals])
        self.logger.info(f'Created product {product_id}')
        return product_id
    
    # === Accounting Methods ===
    
    def get_account_balance(self, account_code: str) -> Dict:
        """Get account balance."""
        account = self._rpc_call(
            'account.account',
            'search_read',
            [[['code', '=', account_code]]],
            {'fields': ['id', 'name', 'code', 'balance']}
        )
        
        return account[0] if account else {}
    
    def get_journal_items(self, journal_id: int = None, 
                          limit: int = 50) -> List[Dict]:
        """Get journal items (accounting entries)."""
        domain = []
        if journal_id:
            domain.append(['journal_id', '=', journal_id])
        
        return self._rpc_call(
            'account.move.line',
            'search_read',
            [domain],
            {
                'fields': ['id', 'date', 'name', 'debit', 'credit', 'balance'],
                'order': 'date desc',
                'limit': limit
            }
        )
    
    # === Reporting Methods ===
    
    def get_financial_summary(self) -> Dict:
        """Get financial summary."""
        summary = {
            'date': datetime.now().isoformat(),
            'receivables': 0,
            'payables': 0,
            'income': 0,
            'expenses': 0
        }
        
        # Get receivables (customer invoices)
        receivables = self._rpc_call(
            'account.move',
            'search_read',
            [[['move_type', '=', 'out_invoice'], ['state', '=', 'posted']]],
            {'fields': ['amount_residual']}
        )
        summary['receivables'] = sum(r.get('amount_residual', 0) for r in receivables)
        
        # Get payables (vendor bills)
        payables = self._rpc_call(
            'account.move',
            'search_read',
            [[['move_type', '=', 'in_invoice'], ['state', '=', 'posted']]],
            {'fields': ['amount_residual']}
        )
        summary['payables'] = sum(r.get('amount_residual', 0) for r in payables)
        
        return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Odoo MCP Server')
    parser.add_argument('--url', type=str, default=os.getenv('ODOO_URL', 'http://localhost:8069'),
                        help='Odoo server URL')
    parser.add_argument('--db', type=str, default=os.getenv('ODOO_DB'),
                        help='Database name')
    parser.add_argument('--user', type=str, default=os.getenv('ODOO_USERNAME'),
                        help='Username')
    parser.add_argument('--password', type=str, default=os.getenv('ODOO_PASSWORD'),
                        help='Password')
    parser.add_argument('--action', type=str, default='summary',
                        choices=['summary', 'invoices', 'partners', 'test'],
                        help='Action to perform')
    
    args = parser.parse_args()
    
    if not args.db or not args.user or not args.password:
        print('Error: Missing Odoo credentials. Use --db, --user, --password or environment variables.')
        exit(1)
    
    try:
        odoo = OdooMCP(
            url=args.url,
            db=args.db,
            username=args.user,
            password=args.password
        )
        
        if args.action == 'summary':
            summary = odoo.get_financial_summary()
            print(json.dumps(summary, indent=2))
        
        elif args.action == 'invoices':
            invoices = odoo.get_invoices(limit=10)
            print(json.dumps(invoices, indent=2))
        
        elif args.action == 'partners':
            partners = odoo.search_partner('')
            print(json.dumps(partners[:10], indent=2))
        
        elif args.action == 'test':
            print('✓ Odoo MCP connection successful')
            print(f'✓ Authenticated as user: {odoo.uid}')
            
    except Exception as e:
        print(f'Error: {e}')
        exit(1)


if __name__ == '__main__':
    main()
