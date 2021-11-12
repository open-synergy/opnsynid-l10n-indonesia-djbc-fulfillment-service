# -*- coding: utf-8 -*-
# Copyright 2021 PT. Simetri Sinergi Indonesia
# Copyright 2021 OpenSynergy Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "DJBC Fullfilment Service",
    "version": "8.0.1.0.0",
    "author": "OpenSynergy Indonesia, PT. Simetri Sinergi Indonesia",
    "website": "https://simetri-sinergi.id",
    "license": "AGPL-3",
    "depends": [
        "l10n_id_djbc_app",
        "stock_picking_fulfillment_service_invoice",
    ],
    "data": [
        "wizards/create_djbc_fullfilment_invoice.xml",
        "views/djbc_custom_document_views.xml",
        "views/stock_fulfillment_service_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
}
