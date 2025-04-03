document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    if (hamburger) {
        hamburger.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }

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

                // 스타일 속성 설정
                path.setAttribute('stroke', connector.stroke);
                path.setAttribute('stroke-width', connector.strokeWidth);
                path.setAttribute('fill', connector.fill);
                if (connector.strokeDasharray) {
                    path.setAttribute('stroke-dasharray', connector.strokeDasharray);
                }

                group.appendChild(path);
                interactiveDiagram.appendChild(group);
            });

            // 모든 연결선 초기화
            initializeAllConnections();
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

            // 방향 결정 (수직/수평)
            const isHorizontal = Math.abs(dx) > Math.abs(dy);

            // 제어점 거리 계산 (거리에 비례하되 최소/최대값 설정)
            const controlDistanceMin = Math.min(distance * 0.3, 60);
            const controlDistanceMax = Math.min(distance * 0.5, 120);

            let controlX1, controlY1, controlX2, controlY2;

            // 요소를 선으로 가리지 않도록 제어점 위치 조정
            if (isHorizontal) {
                // 수평 방향 연결인 경우
                const offsetY = Math.min(Math.abs(dy) * 0.5, 50) * (dy >= 0 ? 1 : -1);

                // 첫 번째 제어점: 출발점에서 수평으로 이동 후 수직 방향으로 약간 휘어짐
                controlX1 = sourceX + controlDistanceMin * (dx >= 0 ? 1 : -1);
                controlY1 = sourceY + offsetY * 0.3;

                // 두 번째 제어점: 도착점에서 수평으로 이동 후 수직 방향으로 약간 휘어짐
                controlX2 = targetX - controlDistanceMin * (dx >= 0 ? 1 : -1);
                controlY2 = targetY + offsetY * 0.3;
            } else {
                // 수직 방향 연결인 경우
                const offsetX = Math.min(Math.abs(dx) * 0.5, 50) * (dx >= 0 ? 1 : -1);

                // 첫 번째 제어점: 출발점에서 수직으로 이동 후 수평 방향으로 약간 휘어짐
                controlX1 = sourceX + offsetX * 0.3;
                controlY1 = sourceY + controlDistanceMin * (dy >= 0 ? 1 : -1);

                // 두 번째 제어점: 도착점에서 수직으로 이동 후 수평 방향으로 약간 휘어짐
                controlX2 = targetX + offsetX * 0.3;
                controlY2 = targetY - controlDistanceMin * (dy >= 0 ? 1 : -1);
            }

            // 대각선 방향 연결인 경우 추가 조정
            if (Math.abs(dx) > 50 && Math.abs(dy) > 50) {
                // 대각선 방향의 경우 더 부드러운 곡선을 위해 제어점 조정
                const midX = (sourceX + targetX) / 2;
                const midY = (sourceY + targetY) / 2;

                // 중간 지점에서 약간 벗어난 위치로 제어점 조정
                const offsetX = Math.min(Math.abs(dx) * 0.2, 40) * (dx >= 0 ? 1 : -1);
                const offsetY = Math.min(Math.abs(dy) * 0.2, 40) * (dy >= 0 ? 1 : -1);

                controlX1 = midX - offsetX + offsetY * 0.5;
                controlY1 = midY - offsetY - offsetX * 0.5;
                controlX2 = midX + offsetX + offsetY * 0.5;
                controlY2 = midY + offsetY - offsetX * 0.5;
            }

            // 3차 베지어 곡선 사용
            return `M${sourceX},${sourceY} C${controlX1},${controlY1} ${controlX2},${controlY2} ${targetX},${targetY}`;
        }

        // 모든 연결선 초기화 함수
        function initializeAllConnections() {
            // 모든 연결선에 대해 경로 계산 및 설정
            document.querySelectorAll('.diagram-connector').forEach(connector => {
                const fromId = connector.getAttribute('data-from');
                const toId = connector.getAttribute('data-to');

                if (!fromId || !toId) return;

                // 소스 및 타겟 요소 찾기
                const sourceElement = document.querySelector(`.diagram-element[data-element-id="${fromId}"]`);
                const targetElement = document.querySelector(`.diagram-element[data-element-id="${toId}"]`);

                if (!sourceElement || !targetElement) return;

                // 연결점 계산
                const connectionPoints = calculateConnectionPoints(sourceElement, targetElement);
                if (!connectionPoints) return;

                // 베지어 곡선 경로 생성
                const pathData = createBezierPath(
                    connectionPoints.sourceX,
                    connectionPoints.sourceY,
                    connectionPoints.targetX,
                    connectionPoints.targetY
                );

                // 경로 설정
                const path = connector.querySelector('path');
                if (path) {
                    path.setAttribute('d', pathData);
                }
            });
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
                    // 스트로크 속성 가져오기
                    const stroke = path.getAttribute('stroke');
                    const strokeWidth = path.getAttribute('stroke-width');
                    const strokeDasharray = path.getAttribute('stroke-dasharray');

                    // 베지어 곡선 경로 생성
                    const pathData = createBezierPath(
                        connectionPoints.sourceX,
                        connectionPoints.sourceY,
                        connectionPoints.targetX,
                        connectionPoints.targetY
                    );

                    // 경로 업데이트
                    path.setAttribute('d', pathData);

                    // 선 스타일 유지
                    path.setAttribute('stroke', stroke);
                    path.setAttribute('stroke-width', strokeWidth);
                    if (strokeDasharray) {
                        path.setAttribute('stroke-dasharray', strokeDasharray);
                    }
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
