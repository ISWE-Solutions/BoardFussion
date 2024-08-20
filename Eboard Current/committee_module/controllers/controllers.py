# -*- coding: utf-8 -*-
# from odoo import http


# class CommitteeModule(http.Controller):
#     @http.route('/committee_module/committee_module', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/committee_module/committee_module/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('committee_module.listing', {
#             'root': '/committee_module/committee_module',
#             'objects': http.request.env['committee_module.committee_module'].search([]),
#         })

#     @http.route('/committee_module/committee_module/objects/<model("committee_module.committee_module"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('committee_module.object', {
#             'object': obj
#         })

