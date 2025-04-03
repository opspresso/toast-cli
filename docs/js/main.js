document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger) {
        hamburger.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }

    // Architecture diagram elements and connectors
    // 다이어그램 요소 정의
    const diagramElements = {
        // 제목
        'title': {
            type: 'title',
            content: [
                { type: 'text', x: 500, y: 50, fontFamily: 'Arial', fontSize: 28, textAnchor: 'middle', fontWeight: 'bold', text: 'Toast-cli Architecture' },
                { type: 'text', x: 500, y: 90, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', fill: '#6c757d', text: 'Plugin-based Design Pattern v3.1.0' }
            ]
        },
        // 메인 CLI 박스
        'main-cli': {
            type: 'box',
            rect: { x: 300, y: 130, width: 400, height: 100, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
            content: [
                { type: 'text', x: 500, y: 175, fontFamily: 'Arial', fontSize: 20, textAnchor: 'middle', text: 'Main CLI Application' },
                { type: 'text', x: 500, y: 205, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', fill: '#6c757d', text: '(toast/__init__.py)' }
            ]
        },
        // 헬퍼 유틸리티 박스
        'helpers': {
            type: 'box',
            rect: { x: 750, y: 130, width: 200, height: 100, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
            content: [
                { type: 'text', x: 850, y: 175, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', text: 'Helper Utilities' },
                { type: 'text', x: 850, y: 205, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: '(toast/helpers.py)' }
            ]
        },
        // 모듈 진입점 박스
        'main-module': {
            type: 'box',
            rect: { x: 50, y: 130, width: 200, height: 100, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
            content: [
                { type: 'text', x: 150, y: 175, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', text: 'Module Entry Point' },
                { type: 'text', x: 150, y: 205, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: '(toast/__main__.py)' }
            ]
        },
        // BasePlugin 박스
        'base-plugin': {
            type: 'box',
            rect: { x: 300, y: 280, width: 400, height: 80, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
            content: [
                { type: 'text', x: 500, y: 320, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', text: 'BasePlugin' },
                { type: 'text', x: 500, y: 345, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: '(toast/plugins/base_plugin.py)' }
            ]
        },
        // 유틸리티 박스
        'utils': {
            type: 'box',
            rect: { x: 750, y: 280, width: 200, height: 80, rx: 10, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 2 },
            content: [
                { type: 'text', x: 850, y: 320, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', text: 'Utilities' },
                { type: 'text', x: 850, y: 345, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: '(toast/plugins/utils.py)' }
            ]
        },
        // 플러그인 행 1
        'am-plugin': {
            type: 'box',
            rect: { x: 50, y: 410, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 130, y: 440, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'AmPlugin' },
                { type: 'text', x: 130, y: 460, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(am_plugin.py)' }
            ]
        },
        'ctx-plugin': {
            type: 'box',
            rect: { x: 230, y: 410, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 310, y: 440, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'CtxPlugin' },
                { type: 'text', x: 310, y: 460, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(ctx_plugin.py)' }
            ]
        },
        'env-plugin': {
            type: 'box',
            rect: { x: 410, y: 410, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 490, y: 440, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'EnvPlugin' },
                { type: 'text', x: 490, y: 460, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(env_plugin.py)' }
            ]
        },
        'git-plugin': {
            type: 'box',
            rect: { x: 590, y: 410, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 670, y: 440, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'GitPlugin' },
                { type: 'text', x: 670, y: 460, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(git_plugin.py)' }
            ]
        },
        // 플러그인 행 2
        'cdw-plugin': {
            type: 'box',
            rect: { x: 50, y: 490, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 130, y: 520, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'CdwPlugin' },
                { type: 'text', x: 130, y: 540, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(cdw_plugin.py)' }
            ]
        },
        'dot-plugin': {
            type: 'box',
            rect: { x: 230, y: 490, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 310, y: 520, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'DotPlugin' },
                { type: 'text', x: 310, y: 540, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(dot_plugin.py)' }
            ]
        },
        'region-plugin': {
            type: 'box',
            rect: { x: 410, y: 490, width: 160, height: 60, rx: 6, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
            content: [
                { type: 'text', x: 490, y: 520, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', text: 'RegionPlugin' },
                { type: 'text', x: 490, y: 540, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: '(region_plugin.py)' }
            ]
        },
        // 통합 박스
        'aws-integration': {
            type: 'box',
            rect: { x: 590, y: 490, width: 360, height: 60, rx: 6, fill: '#f8f9fa', stroke: '#28a745', strokeWidth: 1 },
            content: [
                { type: 'text', x: 770, y: 520, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', fill: '#28a745', text: 'AWS Integration' },
                { type: 'text', x: 770, y: 540, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#28a745', text: '(SSM Parameter Store, EKS, STS, Profiles, Regions)' }
            ]
        },
        // 플러그인 명령 박스
        'plugin-commands': {
            type: 'box',
            rect: { x: 200, y: 600, width: 600, height: 80, rx: 6, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1 },
            content: [
                { type: 'text', x: 500, y: 630, fontFamily: 'Arial', fontSize: 18, textAnchor: 'middle', fontWeight: 'bold', text: 'Plugin Commands' },
                { type: 'text', x: 500, y: 660, fontFamily: 'Arial', fontSize: 14, textAnchor: 'middle', fill: '#6c757d', text: 'am | cdw | ctx | dot | env | git | region | version' }
            ]
        },
        // 외부 의존성 박스
        'dependencies': {
            type: 'box',
            rect: { x: 50, y: 280, width: 200, height: 80, rx: 6, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '5,3' },
            content: [
                { type: 'text', x: 150, y: 310, fontFamily: 'Arial', fontSize: 16, textAnchor: 'middle', fontWeight: 'bold', text: 'Dependencies' },
                { type: 'text', x: 150, y: 335, fontFamily: 'Arial', fontSize: 12, textAnchor: 'middle', fill: '#6c757d', text: 'Click, importlib, pkgutil, fzf, jq, aws-cli, kubectl' }
            ]
        },
        // 범례
        'legend': {
            type: 'legend',
            content: [
                { type: 'rect', x: 250, y: 720, width: 20, height: 20, rx: 2, fill: '#e9f5ff', stroke: '#007bff', strokeWidth: 1 },
                { type: 'text', x: 280, y: 735, fontFamily: 'Arial', fontSize: 14, text: 'Core Components' },
                { type: 'rect', x: 420, y: 720, width: 20, height: 20, rx: 2, fill: '#ffffff', stroke: '#007bff', strokeWidth: 1 },
                { type: 'text', x: 450, y: 735, fontFamily: 'Arial', fontSize: 14, text: 'Plugins' },
                { type: 'rect', x: 550, y: 720, width: 20, height: 20, rx: 2, fill: '#f8f9fa', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '5,3' },
                { type: 'text', x: 580, y: 735, fontFamily: 'Arial', fontSize: 14, text: 'External' },
                { type: 'rect', x: 680, y: 720, width: 20, height: 20, rx: 2, fill: '#f8f9fa', stroke: '#28a745', strokeWidth: 1 },
                { type: 'text', x: 710, y: 735, fontFamily: 'Arial', fontSize: 14, text: 'Integrations' }
            ]
        }
    };

    // 연결선 정의
    const diagramConnectors = [
        // 메인 CLI에서 BasePlugin으로
        { from: 'main-cli', to: 'base-plugin', path: 'M500,230 C500,250 500,260 500,280', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        // 메인 CLI에서 헬퍼 유틸리티로
        { from: 'main-cli', to: 'helpers', path: 'M700,180 C720,180 730,180 750,180', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        // 메인 CLI에서 모듈 진입점으로
        { from: 'main-cli', to: 'main-module', path: 'M300,180 C280,180 270,180 250,180', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        // BasePlugin에서 유틸리티로
        { from: 'base-plugin', to: 'utils', path: 'M700,320 C720,320 730,320 750,320', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        // BasePlugin에서 플러그인 행으로
        { from: 'base-plugin', to: 'am-plugin', path: 'M300,360 C200,380 150,390 130,410', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        { from: 'base-plugin', to: 'ctx-plugin', path: 'M350,360 C330,380 320,390 310,410', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        { from: 'base-plugin', to: 'env-plugin', path: 'M450,360 C470,380 480,390 490,410', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        { from: 'base-plugin', to: 'git-plugin', path: 'M650,360 C660,380 665,390 670,410', stroke: '#007bff', strokeWidth: 2, fill: 'none' },
        // 플러그인 행 1에서 행 2로 연결
        { from: 'am-plugin', to: 'cdw-plugin', path: 'M130,470 C130,475 130,480 130,490', stroke: '#007bff', strokeWidth: 1, fill: 'none' },
        { from: 'ctx-plugin', to: 'dot-plugin', path: 'M310,470 C310,475 310,480 310,490', stroke: '#007bff', strokeWidth: 1, fill: 'none' },
        { from: 'env-plugin', to: 'region-plugin', path: 'M490,470 C490,475 490,480 490,490', stroke: '#007bff', strokeWidth: 1, fill: 'none' },
        { from: 'git-plugin', to: 'aws-integration', path: 'M670,470 C670,475 670,480 670,490 C700,490 730,490 770,490', stroke: '#007bff', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' },
        // 플러그인에서 명령으로 연결
        { from: 'cdw-plugin', to: 'plugin-commands', path: 'M130,550 C130,570 150,580 200,600', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' },
        { from: 'dot-plugin', to: 'plugin-commands', path: 'M310,550 C310,570 320,580 350,600', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' },
        { from: 'region-plugin', to: 'plugin-commands', path: 'M490,550 C490,570 480,580 450,600', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' },
        { from: 'aws-integration', to: 'plugin-commands', path: 'M770,550 C770,570 750,580 700,600', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' },
        // 외부 의존성에서 메인 CLI로
        { from: 'dependencies', to: 'main-cli', path: 'M250,320 C270,320 280,320 300,320', stroke: '#6c757d', strokeWidth: 1, strokeDasharray: '4,2', fill: 'none' }
    ];

    // Architecture diagram drag functionality
    const interactiveDiagram = document.querySelector('.interactive-diagram');
    if (interactiveDiagram) {
        // 초기 SVG 요소 위치 저장을 위한 객체
        const initialPositions = {};
        // 현재 드래그 중인 요소
        let selectedElement = null;
        // 드래그 오프셋
        let offset = { x: 0, y: 0 };
        // 연결선 정보 저장
        const connections = {};

        // SVG 네임스페이스
        const SVG_NS = 'http://www.w3.org/2000/svg';

        // 다이어그램 요소 생성 함수
        function createDiagramElements() {
            // 모든 요소 생성
            for (const [id, element] of Object.entries(diagramElements)) {
                const group = document.createElementNS(SVG_NS, 'g');
                group.classList.add('diagram-element');
                group.setAttribute('data-element-type', element.type);
                group.setAttribute('data-element-id', id);

                // 박스 요소 생성
                if (element.rect) {
                    const rect = document.createElementNS(SVG_NS, 'rect');
                    rect.setAttribute('x', element.rect.x);
                    rect.setAttribute('y', element.rect.y);
                    rect.setAttribute('width', element.rect.width);
                    rect.setAttribute('height', element.rect.height);
                    rect.setAttribute('rx', element.rect.rx);
                    rect.setAttribute('fill', element.rect.fill);
                    rect.setAttribute('stroke', element.rect.stroke);
                    rect.setAttribute('stroke-width', element.rect.strokeWidth);
                    if (element.rect.strokeDasharray) {
                        rect.setAttribute('stroke-dasharray', element.rect.strokeDasharray);
                    }
                    group.appendChild(rect);
                }

                // 내용 요소 생성
                if (element.content) {
                    element.content.forEach(item => {
                        if (item.type === 'text') {
                            const text = document.createElementNS(SVG_NS, 'text');
                            text.setAttribute('x', item.x);
                            text.setAttribute('y', item.y);
                            text.setAttribute('font-family', item.fontFamily);
                            text.setAttribute('font-size', item.fontSize);
                            text.setAttribute('text-anchor', item.textAnchor);
                            if (item.fontWeight) {
                                text.setAttribute('font-weight', item.fontWeight);
                            }
                            if (item.fill) {
                                text.setAttribute('fill', item.fill);
                            }
                            text.textContent = item.text;
                            group.appendChild(text);
                        } else if (item.type === 'rect') {
                            const rect = document.createElementNS(SVG_NS, 'rect');
                            rect.setAttribute('x', item.x);
                            rect.setAttribute('y', item.y);
                            rect.setAttribute('width', item.width);
                            rect.setAttribute('height', item.height);
                            rect.setAttribute('rx', item.rx);
                            rect.setAttribute('fill', item.fill);
                            rect.setAttribute('stroke', item.stroke);
                            rect.setAttribute('stroke-width', item.strokeWidth);
                            if (item.strokeDasharray) {
                                rect.setAttribute('stroke-dasharray', item.strokeDasharray);
                            }
                            group.appendChild(rect);
                        }
                    });
                }

                interactiveDiagram.appendChild(group);
            }

            // 연결선 생성
            diagramConnectors.forEach((connector, index) => {
                const group = document.createElementNS(SVG_NS, 'g');
                group.classList.add('diagram-connector');
                group.setAttribute('data-from', connector.from);
                group.setAttribute('data-to', connector.to);

                const path = document.createElementNS(SVG_NS, 'path');
                path.setAttribute('d', connector.path);
                path.setAttribute('stroke', connector.stroke);
                path.setAttribute('stroke-width', connector.strokeWidth);
                path.setAttribute('fill', connector.fill);
                if (connector.strokeDasharray) {
                    path.setAttribute('stroke-dasharray', connector.strokeDasharray);
                }

                group.appendChild(path);
                interactiveDiagram.appendChild(group);
            });
        }

        // 다이어그램 요소 생성
        createDiagramElements();

        // 모든 다이어그램 요소에 대해 초기 위치 저장
        document.querySelectorAll('.diagram-element').forEach(element => {
            const id = element.getAttribute('data-element-id');
            if (id) {
                // 요소의 초기 위치 저장
                initialPositions[id] = { element, x: 0, y: 0 };

                // 요소에 커서 스타일 적용
                element.style.cursor = 'grab';

                // 요소에 마우스 이벤트 리스너 추가
                element.addEventListener('mousedown', startDrag);
            }
        });

        // 연결선 정보 수집
        document.querySelectorAll('.diagram-connector').forEach(connector => {
            const fromId = connector.getAttribute('data-from');
            const toId = connector.getAttribute('data-to');

            if (fromId && toId) {
                if (!connections[fromId]) connections[fromId] = [];
                if (!connections[toId]) connections[toId] = [];

                connections[fromId].push({ connector, isFrom: true, targetId: toId });
                connections[toId].push({ connector, isFrom: false, targetId: fromId });
            }
        });

        // 드래그 시작 함수
        function startDrag(event) {
            event.preventDefault();

            // 현재 클릭된 요소 (가장 가까운 diagram-element 찾기)
            selectedElement = event.target.closest('.diagram-element');
            if (!selectedElement) return;

            const id = selectedElement.getAttribute('data-element-id');
            if (!id) return;

            // 드래그 중인 요소 스타일 변경
            selectedElement.style.cursor = 'grabbing';
            selectedElement.classList.add('dragging');

            // 현재 요소의 위치 정보
            const position = initialPositions[id];

            // 마우스 위치와 요소 위치의 차이 계산
            offset = {
                x: event.clientX - position.x,
                y: event.clientY - position.y
            };

            // 전역 이벤트 리스너 추가
            document.addEventListener('mousemove', drag);
            document.addEventListener('mouseup', endDrag);
        }

        // 드래그 중 함수
        function drag(event) {
            if (!selectedElement) return;

            event.preventDefault();

            const id = selectedElement.getAttribute('data-element-id');
            if (!id) return;

            // 새 위치 계산
            const newX = event.clientX - offset.x;
            const newY = event.clientY - offset.y;

            // 위치 업데이트
            initialPositions[id].x = newX;
            initialPositions[id].y = newY;

            // 요소에 변환 적용
            selectedElement.setAttribute('transform', `translate(${newX}, ${newY})`);

            // 연결된 선 업데이트
            updateConnections(id);
        }

        // 드래그 종료 함수
        function endDrag() {
            if (!selectedElement) return;

            // 스타일 복원
            selectedElement.style.cursor = 'grab';
            selectedElement.classList.remove('dragging');

            // 전역 이벤트 리스너 제거
            document.removeEventListener('mousemove', drag);
            document.removeEventListener('mouseup', endDrag);

            selectedElement = null;
        }

        // 요소의 중심 좌표와 크기 계산 함수
        function getElementBounds(element) {
            // 요소 내의 rect 요소 찾기
            const rect = element.querySelector('rect');
            if (!rect) return null;

            // rect의 속성 가져오기
            const x = parseFloat(rect.getAttribute('x'));
            const y = parseFloat(rect.getAttribute('y'));
            const width = parseFloat(rect.getAttribute('width'));
            const height = parseFloat(rect.getAttribute('height'));
            const rx = parseFloat(rect.getAttribute('rx') || 0);

            // 요소의 현재 위치 가져오기
            const id = element.getAttribute('data-element-id');
            const position = initialPositions[id] || { x: 0, y: 0 };

            // 중심 좌표 계산
            const centerX = x + width / 2 + position.x;
            const centerY = y + height / 2 + position.y;

            return {
                x, y, width, height, rx,
                centerX, centerY,
                left: x + position.x,
                top: y + position.y,
                right: x + width + position.x,
                bottom: y + height + position.y
            };
        }

        // 두 요소 사이의 연결점 계산 함수
        function calculateConnectionPoints(sourceElement, targetElement) {
            const sourceBounds = getElementBounds(sourceElement);
            const targetBounds = getElementBounds(targetElement);

            if (!sourceBounds || !targetBounds) return null;

            // 두 요소의 중심점 사이의 방향 벡터 계산
            const dx = targetBounds.centerX - sourceBounds.centerX;
            const dy = targetBounds.centerY - sourceBounds.centerY;

            // 방향 벡터 정규화
            const length = Math.sqrt(dx * dx + dy * dy);
            const nx = dx / length;
            const ny = dy / length;

            // 소스 요소의 가장자리 교차점 계산
            let sourceX, sourceY;

            // 수평 방향이 더 강한 경우
            if (Math.abs(nx) > Math.abs(ny)) {
                if (nx > 0) {
                    // 오른쪽 방향
                    sourceX = sourceBounds.right;
                    sourceY = sourceBounds.centerY;
                } else {
                    // 왼쪽 방향
                    sourceX = sourceBounds.left;
                    sourceY = sourceBounds.centerY;
                }
            } else {
                if (ny > 0) {
                    // 아래쪽 방향
                    sourceX = sourceBounds.centerX;
                    sourceY = sourceBounds.bottom;
                } else {
                    // 위쪽 방향
                    sourceX = sourceBounds.centerX;
                    sourceY = sourceBounds.top;
                }
            }

            // 타겟 요소의 가장자리 교차점 계산
            let targetX, targetY;

            // 수평 방향이 더 강한 경우
            if (Math.abs(nx) > Math.abs(ny)) {
                if (nx > 0) {
                    // 오른쪽 방향
                    targetX = targetBounds.left;
                    targetY = targetBounds.centerY;
                } else {
                    // 왼쪽 방향
                    targetX = targetBounds.right;
                    targetY = targetBounds.centerY;
                }
            } else {
                if (ny > 0) {
                    // 아래쪽 방향
                    targetX = targetBounds.centerX;
                    targetY = targetBounds.top;
                } else {
                    // 위쪽 방향
                    targetX = targetBounds.centerX;
                    targetY = targetBounds.bottom;
                }
            }

            return {
                sourceX, sourceY,
                targetX, targetY
            };
        }

        // 베지어 곡선 경로 생성 함수
        function createBezierPath(sourceX, sourceY, targetX, targetY) {
            // 방향 벡터 계산
            const dx = targetX - sourceX;
            const dy = targetY - sourceY;

            // 거리 계산
            const distance = Math.sqrt(dx * dx + dy * dy);

            // 제어점 거리 계산 (거리에 비례)
            const controlDistance = Math.min(distance * 0.4, 80);

            // 제어점 계산
            const controlX1 = sourceX + dx * 0.25;
            const controlY1 = sourceY + dy * 0.25;
            const controlX2 = sourceX + dx * 0.75;
            const controlY2 = sourceY + dy * 0.75;

            // 3차 베지어 곡선 사용
            return `M${sourceX},${sourceY} C${controlX1},${controlY1} ${controlX2},${controlY2} ${targetX},${targetY}`;
        }

        // 연결선 업데이트 함수
        function updateConnections(id) {
            if (!connections[id]) return;

            connections[id].forEach(connection => {
                const { connector, isFrom, targetId } = connection;

                // 현재 요소와 타겟 요소
                const sourceElement = document.querySelector(`.diagram-element[data-element-id="${isFrom ? id : targetId}"]`);
                const targetElement = document.querySelector(`.diagram-element[data-element-id="${isFrom ? targetId : id}"]`);

                if (!sourceElement || !targetElement) return;

                // 연결점 계산
                const connectionPoints = calculateConnectionPoints(sourceElement, targetElement);
                if (!connectionPoints) return;

                // 베지어 곡선 경로 업데이트
                const path = connector.querySelector('path');
                if (path) {
                    const pathData = createBezierPath(
                        connectionPoints.sourceX,
                        connectionPoints.sourceY,
                        connectionPoints.targetX,
                        connectionPoints.targetY
                    );
                    path.setAttribute('d', pathData);
                }
            });
        }

        // 사용자에게 드래그 가능함을 알리는 툴팁 추가
        const tooltip = document.createElement('div');
        tooltip.textContent = '박스를 드래그하여 이동할 수 있습니다';
        tooltip.style.position = 'absolute';
        tooltip.style.top = '10px';
        tooltip.style.left = '50%';
        tooltip.style.transform = 'translateX(-50%)';
        tooltip.style.backgroundColor = 'rgba(0, 123, 255, 0.8)';
        tooltip.style.color = 'white';
        tooltip.style.padding = '5px 10px';
        tooltip.style.borderRadius = '4px';
        tooltip.style.fontSize = '14px';
        tooltip.style.zIndex = '1000';
        tooltip.style.opacity = '0';
        tooltip.style.transition = 'opacity 0.3s ease';

        document.querySelector('.architecture-diagram').appendChild(tooltip);

        // 툴팁 표시
        setTimeout(() => {
            tooltip.style.opacity = '1';

            // 3초 후 툴팁 숨기기
            setTimeout(() => {
                tooltip.style.opacity = '0';

                // 페이드 아웃 후 제거
                setTimeout(() => {
                    tooltip.remove();
                }, 300);
            }, 3000);
        }, 500);
    }

    // Copy buttons functionality
    const copyButtons = document.querySelectorAll('.copy-btn');

    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-clipboard-text');

            // Create a temporary textarea element
            const textarea = document.createElement('textarea');
            textarea.value = textToCopy;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);

            // Select and copy the text
            textarea.select();
            document.execCommand('copy');

            // Remove the textarea
            document.body.removeChild(textarea);

            // Change button text temporarily
            const originalText = this.textContent;
            this.textContent = 'Copied!';

            // Restore original button text after a delay
            setTimeout(() => {
                this.textContent = originalText;
            }, 2000);
        });
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();

            // Skip if it's a link with empty href or just "#"
            if (this.getAttribute('href') === '#' || this.getAttribute('href') === '') {
                return;
            }

            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                // Close mobile menu if open
                if (navLinks.classList.contains('active')) {
                    navLinks.classList.remove('active');
                }

                // Scroll to the target element
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Highlight active section in navigation
    const sections = document.querySelectorAll('section[id]');
    const navItems = document.querySelectorAll('.nav-links a[href^="#"]');

    function highlightActiveSection() {
        const scrollPosition = window.scrollY;

        sections.forEach(section => {
            const sectionTop = section.offsetTop - 100;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navItems.forEach(navItem => {
                    navItem.classList.remove('active');
                    if (navItem.getAttribute('href') === '#' + sectionId) {
                        navItem.classList.add('active');
                    }
                });
            }
        });
    }

    window.addEventListener('scroll', highlightActiveSection);
    highlightActiveSection(); // Highlight active section on page load
});
