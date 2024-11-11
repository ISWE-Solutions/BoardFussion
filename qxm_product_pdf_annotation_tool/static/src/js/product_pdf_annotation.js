/** @odoo-module **/

import { Component, onMounted, onWillStart, useRef} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";

class ProductPDFAnnotation extends Component {
    static template = "qxm_product_pdf_annotation_tool.ProductPDFAnnotation";
    static components = { Layout };

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.table_tbody = useRef("table_tbody");
        this.display = {
            controlPanel: {},
            searchPanel: false,
        };
        this.active_id = this.props.action.context.active_id;
        this.annotateMode = false;

        onWillStart(this.fetchDocumentData.bind(this));
        onMounted(this.initializePDF.bind(this));
    }

    async fetchDocumentData() {
            this.data = await this.rpc("/web/dataset/call_kw/product.document/get_document_data", {
            model: 'product.document',
            method: 'get_document_data',
            args: [this.active_id],
            kwargs: {},
        });
        console.log(this.data);
    }

    async initializePDF() {
        try {
            const pdfContainer = document.getElementById('pdf-container');
            pdfContainer.addEventListener('scroll', this.onScrollPage.bind(this));
            console.log('PDF container loaded',this.data);
            const typedarray = this.base64ToUint8Array(this.data.pdf.datas);

            const pdf = await pdfjsLib.getDocument({ data: typedarray }).promise;
            console.log('PDF loaded');

            const pageList = document.getElementById('page-list');

            for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                await this.renderPDFPage(pdf, pageNum, pdfContainer, pageList);
            }
            this.onScrollPage();
        } catch (reason) {
            console.error(reason);
        }
    }

    base64ToUint8Array(base64) {
        const binaryString = atob(base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes;
    }

    // async renderPDFPage(pdf, pageNum, pdfContainer, pageList) {
    //     const page = await pdf.getPage(pageNum);
    //     console.log('Page loaded');

    //     const scale = 1.3;
    //     const viewport = page.getViewport({ scale });
    //     const pageDiv = this.createPageDiv(pageNum);
    //     const canvasWrapper = this.createCanvasWrapper();
    //     const canvas = this.createCanvas(viewport);

    //     canvasWrapper.appendChild(canvas);
    //     pageDiv.appendChild(canvasWrapper);
    //     pdfContainer.appendChild(pageDiv);

    //     const pagerCanvasWrapper = await this.createPagerCanvasWrapper(page, pageNum, pageDiv, pdfContainer);
    //     pageList.appendChild(pagerCanvasWrapper);

    //     const context = canvas.getContext('2d');
    //     const renderContext = { canvasContext: context, viewport };
    //     await page.render(renderContext).promise;
    //     console.log('Page rendered');

    //     this.initializeMarkers(pageNum, canvasWrapper, canvas);
    // }

    async renderPDFPage(pdf, pageNum, pdfContainer, pageList) {
        const page = await pdf.getPage(pageNum);
        const scale = 1.3;
        const viewport = page.getViewport({ scale });
        const pageDiv = this.createPageDiv(pageNum);
        const canvasWrapper = this.createCanvasWrapper();
        const canvas = this.createCanvas(viewport);
    
        canvasWrapper.appendChild(canvas);
        pageDiv.appendChild(canvasWrapper);
        pdfContainer.appendChild(pageDiv);
    
        const context = canvas.getContext('2d');
        const renderContext = { canvasContext: context, viewport };
        await page.render(renderContext).promise;
    
        // Add the text selection listener after rendering the PDF page
        // this.addTextSelectionListener(canvas, pageNum);
    
        this.initializeMarkers(pageNum, canvasWrapper, canvas);
    }

    // addTextSelectionListener(canvas, pageNum) {
    //     canvas.addEventListener('mouseup', (event) => {
    //         const selection = window.getSelection();
    //         const selectedText = selection.toString();
    
    //         if (selectedText) {
    //             const range = selection.getRangeAt(0);
    //             const { startOffset, endOffset } = range;
    
    //             // Compute bounding box for the selected text and highlight it
    //             const selectedBoxes = this.getSelectedTextBoundingBoxes(range);
    
    //             this.highlightText(selectedBoxes, pageNum);
    //         }
    //     });
    // }



    createTextLayer(textContent, viewport) {
        const textLayerDiv = document.createElement('div');
        textLayerDiv.classList.add('textLayer');
        pdfjsLib.renderTextLayer({
            textContent: textContent,
            container: textLayerDiv,
            viewport: viewport,
            textDivs: [],
        });
        return textLayerDiv;
    }    
    

    createPageDiv(pageNum) {
        const pageDiv = document.createElement('div');
        pageDiv.id = `page-${pageNum}`;
        pageDiv.classList.add('page-div');
        return pageDiv;
    }

    createCanvasWrapper() {
        const canvasWrapper = document.createElement('div');
        canvasWrapper.classList.add('canvas-wrapper');
        return canvasWrapper;
    }

    createCanvas(viewport) {
        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        return canvas;
    }

    async createPagerCanvasWrapper(page, pageNum, pageDiv, pdfContainer) {
        const pagerCanvasWrapper = document.createElement('div');
        pagerCanvasWrapper.id = `sidepage-${pageNum}`;
        pagerCanvasWrapper.classList.add('pager-canvas-wrapper');
        pagerCanvasWrapper.dataset.pageNumber = pageNum;

        const pagerViewport = page.getViewport({ scale: 0.2 });
        const pagerCanvas = this.createCanvas(pagerViewport);
        const pagerContext = pagerCanvas.getContext('2d');
        const renderPager = { canvasContext: pagerContext, viewport: pagerViewport };

        await page.render(renderPager).promise;

        const pageLink = document.createElement('div');
        pageLink.textContent = `${pageNum}`;

        pagerCanvasWrapper.appendChild(pagerCanvas);
        pagerCanvasWrapper.appendChild(pageLink);

        pagerCanvasWrapper.addEventListener('click', () => {
            this.scrollToPage(pageDiv, pdfContainer);
        });

        return pagerCanvasWrapper;
    }

    // initializeHighlightMode(pageNum, canvasWrapper, canvas) {
    
    //     // Toggle highlight mode
    //     document.getElementById('highlightIcon').addEventListener('click', () => {
    //         console.log(this.highlightMode);
    //         this.highlightMode = !this.highlightMode;
    //         console.log(this.highlightMode);
    //         if (this.highlightMode == true) {
    //             document.getElementById('highlightIcon').classList.add('active');
    //             // console.log('Highlight icon activated');
    //         } else {
    //             document.getElementById('highlightIcon').classList.remove('active');
    //             // console.log('Highlight icon deactivated');
    //         }
    //     });
    
    //     // canvas.addEventListener('click', event => {
    //     //     if (this.highlightMode) {
    //     //         const { x, y } = this.getCanvasClickPosition(event, canvas);
    //     //         // Example dimensions for the highlight area
    //     //         const width = 100;
    //     //         const height = 20;
    //     //         this.highlightText(x, y, width, height, canvasWrapper, pageNum);
    //     //     }
    //     // });

    //     let isHighlighting = false;
    //     let startX, startY, highlightDiv;

    //     canvas.addEventListener('mousedown', (event) => {
    //         if (this.highlightMode && event.button === 0) { // Right mouse button
    //             isHighlighting = true;
    //             const { x, y } = this.getCanvasClickPosition(event, canvas);
    //             startX = x;
    //             startY = y;
    //             highlightDiv = this.createHighlightDiv(x, y, 0, 0);
    //             canvasWrapper.appendChild(highlightDiv);
    //             event.preventDefault(); // Prevent context menu
    //         }
    //     });

    //     canvas.addEventListener('mousemove', (event) => {
    //         if (isHighlighting) {
    //             const { x, y } = this.getCanvasClickPosition(event, canvas);
    //             const width = x - startX;
    //             const height = y - startY;
    //             highlightDiv.style.width = `${width}px`;
    //             highlightDiv.style.height = `${height}px`;
    //         }
    //     });

    //     canvas.addEventListener('mouseup', (event) => {
    //         if (isHighlighting && event.button === 0) { // Right mouse button
    //             isHighlighting = false;
    //             const { x, y } = this.getCanvasClickPosition(event, canvas);
    //             const width = x - startX;
    //             const height = y - startY;
    //             this.highlightText(startX, startY, width, height, canvasWrapper, pageNum);
    //         }
    //     });

    //     // Prevent context menu on right click
    //     canvas.addEventListener('contextmenu', (event) => {
    //         if (this.highlightMode) {
    //             event.preventDefault();
    //         }
    //     });
    // }

    initializeHighlightMode(pageNum, canvasWrapper, canvas) {
        // Ensure the highlight icon exists
        const highlightIcon = document.getElementById('highlightIcon');
        if (!highlightIcon) {
            console.error('Highlight icon not found');
            return;
        }
    
        // Check if the event listener is already attached
        if (!highlightIcon.dataset.listenerAttached) {
            highlightIcon.addEventListener('click', () => {
                console.log('Highlight button clicked');
                this.highlightMode = !this.highlightMode;
                console.log('Highlight mode:', this.highlightMode);
                if (this.highlightMode) {
                    highlightIcon.classList.add('active');
                    console.log('Highlight icon activated');
                } else {
                    highlightIcon.classList.remove('active');
                    console.log('Highlight icon deactivated');
                }
            });
            highlightIcon.dataset.listenerAttached = 'true';
        }
    
        let isHighlighting = false;
        let startX, startY, highlightDiv;
    
        canvas.addEventListener('mousedown', (event) => {
            if (this.highlightMode && event.button === 0) { // Left mouse button
                isHighlighting = true;
                const { x, y } = this.getCanvasClickPosition(event, canvas);
                startX = x;
                startY = y;
                highlightDiv = this.createHighlightDiv(x, y, 0, 0);
                canvasWrapper.appendChild(highlightDiv);
                event.preventDefault(); // Prevent default behavior
            }
        });
    
        canvas.addEventListener('mousemove', (event) => {
            if (isHighlighting) {
                const { x, y } = this.getCanvasClickPosition(event, canvas);
                const width = x - startX;
                const height = y - startY;
                highlightDiv.style.width = `${width}px`;
                highlightDiv.style.height = `${height}px`;
            }
        });
    
        canvas.addEventListener('mouseup', (event) => {
            if (isHighlighting && event.button === 0) { // Left mouse button
                isHighlighting = false;
                const { x, y } = this.getCanvasClickPosition(event, canvas);
                const width = x - startX;
                const height = y - startY;
                this.highlightText(startX, startY, width, height, canvasWrapper, pageNum);
            }
        });
    
        // Prevent context menu on right click
        canvas.addEventListener('contextmenu', (event) => {
            if (this.highlightMode) {
                event.preventDefault();
            }
        });
    }

    highlightText(x, y, width, height, canvasWrapper, pageNum) {
        const highlightDiv = this.createHighlightDiv(x, y, width, height);
        canvasWrapper.appendChild(highlightDiv);
        // this.makeHighlighterDraggable(highlightDiv, highlightDiv.id);
        this.saveHighlightData(x, y, width, height, pageNum, highlightDiv.id);
    }

    saveHighlightData(x, y, width, height, pageNum, highlightId) {
        // Save the highlight data to the backend
        this.orm.create("product.pdf.annotation.highlight", [{
            page_no: pageNum,
            layerx: x,
            layery: y,
            width: width,
            height: height,
            document_id: this.active_id,
        }]).then((ids) => {
            highlightId = ids[0];
            this.globalhighlight_id = ids[0];
            console.log('Highlight created', highlightId);
        });
    }
    
    createHighlightDiv(x, y, width, height) {
        const highlightDiv = document.createElement('div');
        highlightDiv.style.position = 'absolute';
        highlightDiv.style.left = `${x}px`;
        highlightDiv.style.top = `${y}px`;
        highlightDiv.style.width = `${width}px`;
        highlightDiv.style.height = `${height}px`;
        highlightDiv.style.backgroundColor = 'yellow';
        highlightDiv.style.opacity = '0.5';
        highlightDiv.classList.add('text_highlight', 'draggable');
        console.log('div id',highlightDiv.id);

        // Add delete button
        // const deleteButton = document.createElement('button');
        // deleteButton.innerText = 'Delete';
        // deleteButton.classList.add('delete_button');
        // deleteButton.onclick = () => this.deleteHighlight(highlightDiv);
        // highlightDiv.appendChild(deleteButton);

        return highlightDiv;
    }

    deleteHighlight(highlightDiv) {
        const highlightId = highlightDiv.id;
        highlightDiv.remove();
        this.orm.unlink("product.pdf.annotation.highlight", [this.globalhighlight_id]);
    }

    // initializeMarkers(pageNum, canvasWrapper, canvas) {
    //     let line_count = 0;

    //     canvas.addEventListener('click', async event => {
    //         const { x, y } = this.getCanvasClickPosition(event, canvas);
    
    //         if (!this.highlightMode) {
    //             line_count += 1;
    //             const line_id = await this.createLine(x, y, pageNum);
    //             console.log('Line created', line_id);
    //             const line_data = await this.orm.searchRead(
    //                 "product.pdf.annotation.line",
    //                 [
    //                   ["id", "=", line_id],
    //                 ],
    //                 ["user_id"]
    //               );
    //             console.log(line_data);
    //             const user_name= line_data[0].user_id[1];
    //             this.createMarkerDOM(x, y, "", line_id, user_name, canvasWrapper, pageNum, line_count);
    //         }
    //     });
    
    //     const lines = this.data.lines[pageNum] || [];
    //     for (const line of lines) {
    //         line_count += 1;
    //         this.createMarkerDOM(line.layerx, line.layery, line.description || "", line.id, line.user_id[1], canvasWrapper, pageNum, line_count);
    //     }
    
    //     this.initializeHighlightMode(pageNum, canvasWrapper, canvas);
    //     this.loadHighlightData(pageNum, canvasWrapper);
    // }

    // OLD BASIC
    // initializeMarkers(pageNum, canvasWrapper, canvas) {
    //     let line_count = 0;

    //     canvas.addEventListener('click', async event => {
    //         const { x, y } = this.getCanvasClickPosition(event, canvas);
    
    //         if (!this.highlightMode) {
    //             line_count += 1;
    //             const line_id = await this.createLine(x, y, pageNum);
    //             console.log('Line created', line_id);
    //             const line_data = await this.orm.searchRead(
    //                 "product.pdf.annotation.line",
    //                 [
    //                   ["id", "=", line_id],
    //                 ],
    //                 ["user_id"]
    //               );
    //             console.log(line_data);
    //             const user_name= line_data[0].user_id[1];
    //             this.createMarkerDOM(x, y, "", line_id, user_name, canvasWrapper, pageNum, line_count);
    //         }
    //     });
    
    //     const lines = this.data.lines[pageNum] || [];
    //     for (const line of lines) {
    //         line_count += 1;
    //         this.createMarkerDOM(line.layerx, line.layery, line.description || "", line.id, line.user_id[1], canvasWrapper, pageNum, line_count);
    //     }
    
    //     this.initializeHighlightMode(pageNum, canvasWrapper, canvas);
    //     this.loadHighlightData(pageNum, canvasWrapper);
    // }

    async loadHighlightData(pageNum, canvasWrapper) {
        const highlights = this.data.highlighted_marks[pageNum] || [];
        for (const highlight of highlights) {
            this.highlightText(highlight.layerx, highlight.layery, highlight.width, highlight.height, canvasWrapper);
        }
    }

    // WORKING !!!
    initializeMarkers(pageNum, canvasWrapper, canvas) {

        let line_count = 0;
        let isDrawing = false;
        let startX, startY, markerDiv;
        let record_id=0;

        // Ensure the annotate icon exists
        const annotateIcon = document.getElementById('annotateIcon');
        if (!annotateIcon) {
            console.error('Annotate icon not found');
            return;
        }

        // Check if the event listener is already attached
        if (!annotateIcon.dataset.listenerAttached) {
            annotateIcon.addEventListener('click', () => {
                console.log('Annotate button clicked');
                this.annotateMode = !this.annotateMode;
                console.log('Annotate mode:', this.annotateMode);
                if (this.annotateMode) {
                    annotateIcon.classList.add('active');
                    console.log('Annotate icon activated');
                    // this.enableAnnotation(canvas, canvasWrapper, pageNum);
                } else {
                    annotateIcon.classList.remove('active');
                    console.log('Annotate icon deactivated');
                    // this.disableAnnotation(canvas);
                }
            });
            annotateIcon.dataset.listenerAttached = 'true';
        }
    
        // // Check if the event listener is already attached
        // if (!annotateIcon.dataset.listenerAttached) {
        //     annotateIcon.addEventListener('click', () => {
        //         console.log('Annotate button clicked');
        //         console.log('Annotate Mode',this.annotateMode);
        //         this.annotateMode = !this.annotateMode;
        //         console.log('Annotate mode:', this.annotateMode);
        //         if (this.annotateIcon) {
        //             annotateIcon.classList.add('active');
        //             console.log('Annotate icon activated');
        //         } else {
        //             annotateIcon.classList.remove('active');
        //             console.log('Annotate icon deactivated');
        //         }
        //     });
        //     annotateIcon.dataset.listenerAttached = 'true';
        // }

        canvas.addEventListener('mousedown', async event => {
            if (this.annotateMode && event.button === 0) {
                const { x, y } = this.getCanvasClickPosition(event, canvas);
                startX = x;
                startY = y;
                isDrawing = true;
                console.log('X',x);
                console.log('Y',y);
                
                // Create a new line in the backend
                const line_id = await this.createLine(x, y, pageNum);
                console.log('Line created', line_id);

                const line_data = await this.orm.searchRead(
                    "product.pdf.annotation.line",
                    [
                        ["id", "=", line_id],
                    ],
                    ["user_id"]
                );

                console.log('ZEROO',line_data);
                console.log('IDDD',line_data[0].id);
                record_id = line_data[0].id;
                const user_name = line_data[0].user_id[1];
        
                // Create the marker div
                markerDiv = this.createMarkerDiv(x, y, line_id);
                canvasWrapper.appendChild(markerDiv);
        
                // Create the table row
                const newTableRow = this.createTableRow(line_id, "", user_name, pageNum, line_count, markerDiv);
                this.table_tbody.el.appendChild(newTableRow);
        
                // Make the marker draggable
                this.makeDraggable(markerDiv, line_id);
            }

        });
    
        canvas.addEventListener('mousemove', event => {
            if (isDrawing && markerDiv) {
                const { x, y } = this.getCanvasClickPosition(event, canvas);
                const width = x - startX;
                const height = y - startY;
                markerDiv.style.width = `${width}px`;
                markerDiv.style.height = `${height}px`;
            }
        });
    
        canvas.addEventListener('mouseup', event => {
            if (this.annotateMode && event.button === 0) {
                isDrawing = false;
                const { x, y } = this.getCanvasClickPosition(event, canvas);
                const width = x - startX;
                const height = y - startY;
                this.updateLine(record_id, {height: height, width: width});
                // this.saveHighlightData(startX, startY, width, height, pageNum, markerDiv);
            }
        });

        // Prevent context menu on right click
        canvas.addEventListener('contextmenu', (event) => {
            if (this.annotateMode) {
                event.preventDefault();
            }
        });
    
        const lines = this.data.lines[pageNum] || [];
        for (const line of lines) {
            line_count += 1;
            this.createMarkerDOM(line.layerx, line.layery, line.height, line.width, line.description || "", line.id, line.user_id[1], canvasWrapper, pageNum, line_count);
        }
    }

    // initializeMarkers(pageNum, canvasWrapper, canvas) {
    //     // Ensure the annotate icon exists
    //     const annotateIcon = document.getElementById('annotateIcon');
    //     if (!annotateIcon) {
    //         console.error('Annotate icon not found');
    //         return;
    //     }
    
    //     // Check if the event listener is already attached
    //     if (!annotateIcon.dataset.listenerAttached) {
    //         annotateIcon.addEventListener('click', () => {
    //             console.log('Annotate button clicked');
    //             this.annotateMode = !this.annotateMode;
    //             console.log('Annotate mode:', this.annotateMode);
    //             if (this.annotateMode) {
    //                 annotateIcon.classList.add('active');
    //                 console.log('Annotate icon activated');
    //                 this.enableAnnotation(canvas, canvasWrapper, pageNum);
    //             } else {
    //                 annotateIcon.classList.remove('active');
    //                 console.log('Annotate icon deactivated');
    //                 this.disableAnnotation(canvas);
    //             }
    //         });
    //         annotateIcon.dataset.listenerAttached = 'true';
    //     }
    
    //     // Initialize existing markers
    //     let line_count = 0;
    //     const lines = this.data.lines[pageNum] || [];
    //     for (const line of lines) {
    //         line_count += 1;
    //         this.createMarkerDOM(line.layerx, line.layery, line.description || "", line.id, line.user_id[1], canvasWrapper, pageNum, line_count);
    //     }
    // }
    
    

    getCanvasClickPosition(event, canvas) {
        const rect = canvas.getBoundingClientRect();
        const x = (event.clientX - rect.left) - 3;
        const y = (event.clientY - rect.top) - 4;
        return { x, y };
    }

    // The one with highlighter
    // initializeMarkers(pageNum, canvasWrapper, canvas) {
    //     let line_count = 0;
    
    //     let isDrawing = false;
    //     let startX, startY, highlightDiv;
    
    //     canvas.addEventListener('mousedown', async event => {
    //         const { x, y } = this.getCanvasClickPosition(event, canvas);
    
    //         if (!this.highlightMode) {
    //             line_count += 1;
    //             const line_id = await this.createLine(x, y, pageNum);
    //             console.log('Line created', line_id);
    //             const line_data = await this.orm.searchRead(
    //                 "product.pdf.annotation.line",
    //                 [
    //                     ["id", "=", line_id],
    //                 ],
    //                 ["user_id"]
    //             );
    //             console.log(line_data);
    //             const user_name = line_data[0].user_id[1];
    //             this.createMarkerDOM(x, y, "", line_id, user_name, canvasWrapper, pageNum, line_count);
    //         } else {
    //             isDrawing = true;
    //             startX = x;
    //             startY = y;
    //             highlightDiv = this.createHighlightDiv(x, y, 0, 0);
    //             canvasWrapper.appendChild(highlightDiv);
    //         }
    //     });
    
    //     canvas.addEventListener('mousemove', event => {
    //         if (isDrawing) {
    //             const { x, y } = this.getCanvasClickPosition(event, canvas);
    //             const width = x - startX;
    //             const height = y - startY;
    //             highlightDiv.style.width = `${width}px`;
    //             highlightDiv.style.height = `${height}px`;
    //         }
    //     });
    
    //     canvas.addEventListener('mouseup', event => {
    //         if (isDrawing) {
    //             isDrawing = false;
    //             const { x, y } = this.getCanvasClickPosition(event, canvas);
    //             const width = x - startX;
    //             const height = y - startY;
    //             this.saveHighlightData(startX, startY, width, height, pageNum, highlightDiv);
    //         }
    //     });
    
    //     const lines = this.data.lines[pageNum] || [];
    //     for (const line of lines) {
    //         line_count += 1;
    //         this.createMarkerDOM(line.layerx, line.layery, line.description || "", line.id, line.user_id[1], canvasWrapper, pageNum, line_count);
    //     }
    
    //     this.initializeHighlightMode(pageNum, canvasWrapper, canvas);
    //     this.loadHighlightData(pageNum, canvasWrapper);
    // }

    createMarkerDOM(x, y, height, width, description, line_id,user, canvasWrapper, pageNum, line_count) {
        console.log(user,'test');
        const markerDiv = this.createMarkerDiv(x, y, line_id, width, height );
        canvasWrapper.appendChild(markerDiv);
        const newTableRow = this.createTableRow(line_id, description,user, pageNum, line_count, markerDiv);
        this.table_tbody.el.appendChild(newTableRow);
        this.makeDraggable(markerDiv, line_id);
                                               
    }

    createMarkerDiv(x, y, line_id, width, height) {
        const markerDiv = document.createElement('div');
        markerDiv.style.position = 'absolute';
        markerDiv.style.left = `${x}px`;
        markerDiv.style.top = `${y}px`;
        markerDiv.style.width = `${width}px`;
        markerDiv.style.height = `${height}px`;
        markerDiv.style.backgroundColor = 'yellow';
        markerDiv.style.opacity = '0.5';
        markerDiv.id = `marker_${line_id}`;
        // markerDiv.classList.add('text_highlight', 'draggable');
        // console.log('div id',highlightDiv.id);
        return markerDiv;

        // const markerDiv = document.createElement('div');
        // markerDiv.style.position = 'absolute';
        // markerDiv.style.left = `${x}px`;
        // markerDiv.style.top = `${y}px`;
        // markerDiv.style.width = `${width}px`;
        // markerDiv.style.height = `${height}px`;
        // markerDiv.style.backgroundColor = isHighlighter ? 'yellow' : 'red'; // Use yellow for highlighter, red for marker
        // markerDiv.style.opacity = isHighlighter ? '0.5' : '1'; // Semi-transparent for highlighter
        // markerDiv.style.borderRadius = isHighlighter ? '0' : '50%'; // No border radius for highlighter, full border radius for marker
        // markerDiv.id = `marker_${line_id}`;
        // markerDiv.classList.add('text_highlight', 'draggable');
        // return markerDiv;
    }

    // createMarkerDiv(x, y, line_id) {
    //     const markerDiv = document.createElement('div');
    //     markerDiv.style.left = `${x}px`;
    //     markerDiv.style.top = `${y}px`;
    //     markerDiv.id = `marker_${line_id}`;
    //     markerDiv.classList.add('img_marker');
    //     return markerDiv;
    // }

    async createLine(x, y, page_no) {
        const [line_id] = await this.orm.create("product.pdf.annotation.line", [{
            page_no,
            layerx: x,
            layery: y,
            document_id: this.active_id
        }]);
        return line_id;
    }

    async updateLine(resId, data) {
        await this.orm.write("product.pdf.annotation.line", [resId], data);
    }

    async updateHighlighter(resId, data) {
        await this.orm.write("product.pdf.annotation.hiighlight", [resId], data);
    }

    makeHighlighterDraggable(element, highlightId) {
        let offsetX, offsetY;

        element.addEventListener('mousedown', (e) => {
            offsetX = e.clientX - parseInt(element.style.left);
            offsetY = e.clientY - parseInt(element.style.top);
            document.addEventListener('mousemove', moveElement);
            document.addEventListener('mouseup', stopMovingElement);
        });

        const moveElement = (e) => {
            element.style.left = `${e.clientX - offsetX}px`;
            element.style.top = `${e.clientY - offsetY}px`;
        };

        const stopMovingElement = () => {
            document.removeEventListener('mousemove', moveElement);
            document.removeEventListener('mouseup', stopMovingElement);
            this.saveHighlightPosition(highlightId, parseInt(element.style.left), parseInt(element.style.top));
        };
    }

    saveHighlightPosition(highlightId, x, y) {
        this.orm.write("product.pdf.annotation.highlight", [highlightId], {
            layerx: x,
            layery: y,
        });
    }

    // Make an element draggable
    makeDraggable(elem, line_id) {
        var self = this;
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

        elem.onmousedown = dragMouseDown;

        function dragMouseDown(e) {
            e = e || window.event;
            e.preventDefault();
            // Get the mouse cursor position at startup
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = closeDragElement;
            // Call a function whenever the cursor moves
            document.onmousemove = elementDrag;
        }

        function elementDrag(e) {
            e = e || window.event;
            e.preventDefault();
            // Calculate the new cursor position
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;

            // Get the new position
            let newTop = elem.offsetTop - pos2;
            let newLeft = elem.offsetLeft - pos1;

            // Get parent boundaries
            const parentRect = elem.parentElement.getBoundingClientRect();
            const elemRect = elem.getBoundingClientRect();

            // Ensure the element stays within the parent's boundaries
            if (newTop < 0) {
                newTop = 0;
            } else if (newTop + elemRect.height > parentRect.height) {
                newTop = parentRect.height - elemRect.height;
            }

            if (newLeft < 0) {
                newLeft = 0;
            } else if (newLeft + elemRect.width > parentRect.width) {
                newLeft = parentRect.width - elemRect.width;
            }

            // Set the element's new position
            elem.style.top = newTop + "px";
            elem.style.left = newLeft + "px";
        }

        function closeDragElement(e) {
            // Stop moving when mouse button is released
            document.onmouseup = null;
            document.onmousemove = null;
            self.updateLine(line_id, { layerx: elem.style.left.replace('px', ''), layery: elem.style.top.replace('px', '') });
        }
    }

    createTableRow(rowId, description,user, pageNumber, lineNumber, markerDiv) {
        const tr = document.createElement('tr');
        tr.id = `table_line_${rowId}`;
        tr.className = 'table_tr_line';
        tr.innerHTML = `
            <th scope="row"><span>${pageNumber}</span></th>
            <th scope="row"><span>${user}</span></th>
            <td><textarea class="form-control table_tbody_input custom-description-textarea" placeholder="Description ..">${description}</textarea></td>
            <td><i class="fa fa-trash delete_marker" style="cursor: pointer;" aria-hidden="true"></i></td>
        `;

        tr.onmouseover = () => this.addHoverEffect(markerDiv, tr);
        tr.onmouseout = () => this.removeHoverEffect();
        tr.onclick = () => this.scrollToElement(markerDiv);

        markerDiv.onmouseover = () => this.addHoverEffect(markerDiv, tr);
        markerDiv.onmouseout = () => this.removeHoverEffect();
        markerDiv.onclick = () => this.scrollToElement(tr);

        this.initializeDeleteMarker(tr, markerDiv, rowId);
        this.initializeSaveMarker(tr, rowId);

        return tr;
    }

    addHoverEffect(markerDiv, tr) {
        document.querySelectorAll('.marker_hover').forEach(el => el.classList.remove('marker_hover'));
        markerDiv.classList.add('marker_hover');
        tr.classList.add('marker_hover');
    }

    removeHoverEffect() {
        document.querySelectorAll('.marker_hover').forEach(el => el.classList.remove('marker_hover'));
    }

    scrollToElement(element) {
        const container = document.getElementById(element.classList.contains('img_marker') ? 'pdf-container' : 'description_container');
        const containerRect = container.getBoundingClientRect();
        const elementRect = element.getBoundingClientRect();

        const scrollTop = (elementRect.top - 200) - containerRect.top + container.scrollTop;

        container.scrollTo({ top: scrollTop, behavior: 'smooth' });
    }

    initializeDeleteMarker(tr, markerDiv, rowId) {
        const deleteIcon = tr.querySelector('.delete_marker');
        deleteIcon.onclick = () => {
            // First confirmation prompt
            const firstConfirmation = confirm("Are you sure you want to delete this item?");
            if (firstConfirmation) {
                    tr.remove();
                    markerDiv.remove();
                    this.orm.unlink("product.pdf.annotation.line", [rowId]);
            }
        };
    }


    initializeSaveMarker(tr, rowId) {
        const inputField = tr.querySelector('.table_tbody_input');
        inputField.onchange = () => {
            this.updateLine(rowId, { description: inputField.value });
        };
    }

    onScrollPage() {
        const pages = document.getElementById('pdf-container').querySelectorAll('[id^="page-"]');
        const pagerItems = document.getElementById('page-list').querySelectorAll('[id^="sidepage-"]');
        const scrollTop = document.getElementById('pdf-container').scrollTop;
        const containerHeight = document.getElementById('pdf-container').clientHeight;

        let currentPage = 0;
        pages.forEach((page, index) => {
            if (scrollTop >= page.offsetTop - containerHeight / 2) {
                currentPage = index;
            }
        });

        pagerItems.forEach((item, index) => {
            if (index === currentPage) {
                item.firstChild.classList.add('active');
                document.getElementById('page-list').scrollTop = item.offsetTop - document.getElementById('page-list').clientHeight / 2;
            } else {
                item.firstChild.classList.remove('active');
            }
        });
    }

    scrollToPage(pageDiv, pdfContainer) {
        const containerRect = pdfContainer.getBoundingClientRect();
        const pageRect = pageDiv.getBoundingClientRect();
        const scrollTop = pageRect.top - containerRect.top + pdfContainer.scrollTop;

        pdfContainer.scrollTop = scrollTop;
    }
}

registry.category("actions").add("qxm_product_pdf_annotation_tool.product_pdf_annotation", ProductPDFAnnotation);
