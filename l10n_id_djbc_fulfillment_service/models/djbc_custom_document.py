# -*- coding: utf-8 -*-
# Copyright 2021 PT. Simetri Sinergi Indonesia
# Copyright 2021 OpenSynergy Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import fields, models


class DJBCCustomDocument(models.Model):
    _inherit = "l10n_id.djbc_custom_document"

    fullfilment_invoice_ids = fields.Many2many(
        string="Fullfilment Invoices",
        comodel_name="account.invoice",
        relation="rel_djbc_custom_document_2_fullfilment_invoice",
        column1="document_id",
        column2="invoice_id",
    )
