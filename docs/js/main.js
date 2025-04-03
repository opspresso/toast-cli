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

        // 연결선 업데이트 함수
        function updateConnections(id) {
            if (!connections[id]) return;

            connections[id].forEach(connection => {
                const { connector, isFrom, targetId } = connection;

                // 현재 요소와 타겟 요소의 위치
                const sourcePos = initialPositions[id];
                const targetPos = initialPositions[targetId];

                // 원본 라인 좌표 저장 (처음 로드 시 좌표)
                if (!connector.hasAttribute('data-original-coords')) {
                    const lines = connector.querySelectorAll('line');
                    const polygons = connector.querySelectorAll('polygon');

                    // 라인 원본 좌표 저장
                    if (lines.length > 0) {
                        const lineCoords = Array.from(lines).map(line => ({
                            x1: parseFloat(line.getAttribute('x1')),
                            y1: parseFloat(line.getAttribute('y1')),
                            x2: parseFloat(line.getAttribute('x2')),
                            y2: parseFloat(line.getAttribute('y2'))
                        }));
                        connector.setAttribute('data-original-lines', JSON.stringify(lineCoords));
                    }

                    // 폴리곤 원본 좌표 저장
                    if (polygons.length > 0) {
                        const polygonCoords = Array.from(polygons).map(polygon =>
                            polygon.getAttribute('points')
                        );
                        connector.setAttribute('data-original-polygons', JSON.stringify(polygonCoords));
                    }
                }

                // 원본 좌표 가져오기
                const originalLines = JSON.parse(connector.getAttribute('data-original-lines') || '[]');
                const originalPolygons = JSON.parse(connector.getAttribute('data-original-polygons') || '[]');

                // 연결선의 모든 라인 요소 업데이트
                connector.querySelectorAll('line').forEach((line, index) => {
                    if (index >= originalLines.length) return;

                    const origLine = originalLines[index];

                    // 시작점과 끝점 업데이트
                    if (isFrom) {
                        // 시작점이 현재 요소에 연결된 경우
                        line.setAttribute('x1', origLine.x1 + sourcePos.x);
                        line.setAttribute('y1', origLine.y1 + sourcePos.y);
                        // 끝점은 타겟 요소에 연결
                        line.setAttribute('x2', origLine.x2 + targetPos.x);
                        line.setAttribute('y2', origLine.y2 + targetPos.y);
                    } else {
                        // 끝점이 현재 요소에 연결된 경우
                        line.setAttribute('x2', origLine.x2 + sourcePos.x);
                        line.setAttribute('y2', origLine.y2 + sourcePos.y);
                        // 시작점은 타겟 요소에 연결
                        line.setAttribute('x1', origLine.x1 + targetPos.x);
                        line.setAttribute('y1', origLine.y1 + targetPos.y);
                    }
                });

                // 화살표(폴리곤) 업데이트
                connector.querySelectorAll('polygon').forEach((polygon, index) => {
                    if (index >= originalPolygons.length) return;

                    const origPoints = originalPolygons[index];
                    const points = origPoints.split(' ');

                    let updatedPoints;
                    if (isFrom) {
                        // 화살표가 타겟 요소를 가리키는 경우
                        updatedPoints = points.map(point => {
                            const [x, y] = point.split(',').map(parseFloat);
                            // 화살표 위치 계산 - 타겟 요소 위치 기준
                            return `${x + targetPos.x},${y + targetPos.y}`;
                        });
                    } else {
                        // 화살표가 현재 요소를 가리키는 경우
                        updatedPoints = points.map(point => {
                            const [x, y] = point.split(',').map(parseFloat);
                            // 화살표 위치 계산 - 현재 요소 위치 기준
                            return `${x + sourcePos.x},${y + sourcePos.y}`;
                        });
                    }

                    // 업데이트된 포인트 설정
                    polygon.setAttribute('points', updatedPoints.join(' '));
                });
            });

            // 모든 연결선 업데이트 (양쪽 끝점이 모두 이동한 경우 처리)
            document.querySelectorAll('.diagram-connector').forEach(connector => {
                const fromId = connector.getAttribute('data-from');
                const toId = connector.getAttribute('data-to');

                if (fromId && toId && fromId !== id && toId !== id) {
                    const fromPos = initialPositions[fromId];
                    const toPos = initialPositions[toId];

                    // 원본 좌표가 저장되어 있는지 확인
                    if (!connector.hasAttribute('data-original-lines')) {
                        const lines = connector.querySelectorAll('line');
                        const polygons = connector.querySelectorAll('polygon');

                        // 라인 원본 좌표 저장
                        if (lines.length > 0) {
                            const lineCoords = Array.from(lines).map(line => ({
                                x1: parseFloat(line.getAttribute('x1')),
                                y1: parseFloat(line.getAttribute('y1')),
                                x2: parseFloat(line.getAttribute('x2')),
                                y2: parseFloat(line.getAttribute('y2'))
                            }));
                            connector.setAttribute('data-original-lines', JSON.stringify(lineCoords));
                        }

                        // 폴리곤 원본 좌표 저장
                        if (polygons.length > 0) {
                            const polygonCoords = Array.from(polygons).map(polygon =>
                                polygon.getAttribute('points')
                            );
                            connector.setAttribute('data-original-polygons', JSON.stringify(polygonCoords));
                        }
                    }

                    // 원본 좌표 가져오기
                    const originalLines = JSON.parse(connector.getAttribute('data-original-lines') || '[]');
                    const originalPolygons = JSON.parse(connector.getAttribute('data-original-polygons') || '[]');

                    // 라인 업데이트
                    connector.querySelectorAll('line').forEach((line, index) => {
                        if (index >= originalLines.length) return;

                        const origLine = originalLines[index];

                        // 시작점과 끝점 업데이트
                        line.setAttribute('x1', origLine.x1 + fromPos.x);
                        line.setAttribute('y1', origLine.y1 + fromPos.y);
                        line.setAttribute('x2', origLine.x2 + toPos.x);
                        line.setAttribute('y2', origLine.y2 + toPos.y);
                    });

                    // 화살표 업데이트
                    connector.querySelectorAll('polygon').forEach((polygon, index) => {
                        if (index >= originalPolygons.length) return;

                        const origPoints = originalPolygons[index];
                        const points = origPoints.split(' ');

                        // 화살표는 보통 끝점(toId)에 위치
                        const updatedPoints = points.map(point => {
                            const [x, y] = point.split(',').map(parseFloat);
                            return `${x + toPos.x},${y + toPos.y}`;
                        });

                        polygon.setAttribute('points', updatedPoints.join(' '));
                    });
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

    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        const isClickInsideNav = navLinks.contains(event.target);
        const isClickOnHamburger = hamburger.contains(event.target);

        if (!isClickInsideNav && !isClickOnHamburger && navLinks.classList.contains('active')) {
            navLinks.classList.remove('active');
        }
    });

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
