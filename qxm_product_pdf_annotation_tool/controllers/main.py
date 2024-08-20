# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleDelivery(WebsiteSale):

    @http.route(['/shop/product/document'], type='json', auth='public', methods=['POST'], website=True)
    def get_document_data(self, document_id, **kw):
        rec = request.env['product.document'].sudo().browse([document_id])
        return rec.get_document_data()
