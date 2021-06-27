# -*- coding: utf-8 -*-

{
    'name': 'Stock by purchase order',
    'version': '11.0',
    'category': 'Purchase',
    'sequence': 95,
    'summary': 'Available stock by purchase order',
    'description': """
    For a traceability between your purchases and your sales,
    we offer you this module which allows you to link the delivery 
    with the purchase orders, and to display the stock by purchase
""",
    'website': '',
    'depends': ['purchase','stock'],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_move.xml",
        "views/wizard_purchase_list.xml",

    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}
