// 3D Architecture diagram functionality
document.addEventListener('DOMContentLoaded', function() {
    // 3D 다이어그램 컨테이너 요소
    const container = document.getElementById('diagram-3d');
    if (!container) return;

    // 툴팁 요소 생성
    const tooltip = document.createElement('div');
    tooltip.className = 'element-tooltip';
    document.body.appendChild(tooltip);

    // Three.js 변수
    let scene, camera, renderer, controls;
    let raycaster, mouse;
    let autoRotate = true;
    let hoveredObject = null;

    // 객체 그룹
    const groups = {
        core: new THREE.Group(),
        plugins: new THREE.Group(),
        external: new THREE.Group(),
        integrations: new THREE.Group(),
        connectors: new THREE.Group()
    };

    // 색상 정의
    const colors = {
        core: {
            fill: new THREE.Color('#e9f5ff'),
            stroke: new THREE.Color('#007bff')
        },
        plugins: {
            fill: new THREE.Color('#ffffff'),
            stroke: new THREE.Color('#007bff')
        },
        external: {
            fill: new THREE.Color('#f8f9fa'),
            stroke: new THREE.Color('#6c757d')
        },
        integrations: {
            fill: new THREE.Color('#f8f9fa'),
            stroke: new THREE.Color('#28a745')
        },
        text: new THREE.Color('#343a40'),
        textSecondary: new THREE.Color('#6c757d')
    };

    // 3D 객체 매핑 (ID -> 3D 객체)
    const objectMap = {};
    // 연결점 정보 저장 (ID -> 연결점 객체들)
    const connectionPointsMap = {};
    // 연결선 정보 저장
    const connections = [];

    // 초기화 함수
    function init() {
        // 씬 생성
        scene = new THREE.Scene();
        scene.background = new THREE.Color('#f8f9fa');

        // 카메라 설정
        const width = container.clientWidth || 1000;
        const height = container.clientHeight || 800;
        camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 2000);
        camera.position.set(0, 400, 1000);

        // 렌더러 설정
        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);

        // 디버깅을 위한 콘솔 로그
        console.log('Three.js 초기화 완료');
        console.log('컨테이너 크기:', width, height);

        // 조명 설정
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(0, 200, 100);
        directionalLight.castShadow = true;
        scene.add(directionalLight);

        // 컨트롤 설정
        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.screenSpacePanning = true; // 화면 공간 패닝 활성화
        controls.minDistance = 100;
        controls.maxDistance = 1500;
        controls.maxPolarAngle = Math.PI / 1.5;
        controls.autoRotate = autoRotate;
        controls.autoRotateSpeed = 0.5;

        // 마우스 버튼 설정 변경
        controls.mouseButtons = {
            LEFT: THREE.MOUSE.ROTATE,    // 왼쪽 버튼: 회전
            MIDDLE: THREE.MOUSE.DOLLY,   // 중간 버튼: 줌
            RIGHT: THREE.MOUSE.PAN       // 오른쪽 버튼: 패닝(이동)
        };

        // 레이캐스터 설정 (마우스 상호작용용)
        raycaster = new THREE.Raycaster();
        mouse = new THREE.Vector2();

        // 그룹 추가 및 중앙 정렬
        Object.values(groups).forEach(group => {
            // 그룹을 중앙으로 이동
            group.position.set(0, 0, 0);
            scene.add(group);
        });

        // 요소 생성
        createElements();
        createConnectors();

        // 이벤트 리스너 추가
        window.addEventListener('resize', onWindowResize);
        container.addEventListener('mousemove', onMouseMove);
        container.addEventListener('click', onMouseClick);

        // 컨트롤 버튼 이벤트 리스너
        const resetButton = document.getElementById('reset-camera');
        if (resetButton) {
            resetButton.addEventListener('click', resetCamera);
        }

        const rotationToggle = document.getElementById('toggle-rotation');
        if (rotationToggle) {
            rotationToggle.addEventListener('change', function() {
                autoRotate = this.checked;
                controls.autoRotate = autoRotate;
            });
        }

        // 애니메이션 시작
        animate();
    }

    // 연결점 생성 함수
    function createConnectionPoints(box, id) {
        const width = box.geometry.parameters.width;
        const height = box.geometry.parameters.height;
        const depth = box.geometry.parameters.depth;
        const position = box.position.clone();

        // 연결점 크기
        const pointSize = 3;

        // 연결점 재질 (반투명 구체)
        const pointMaterial = new THREE.MeshBasicMaterial({
            color: 0x007bff,
            transparent: true,
            opacity: 0.7
        });

        // 연결점 위치 (좌, 우, 상, 하)
        const points = {
            left: new THREE.Vector3(position.x - width/2, position.y, position.z),
            right: new THREE.Vector3(position.x + width/2, position.y, position.z),
            top: new THREE.Vector3(position.x, position.y + height/2, position.z),
            bottom: new THREE.Vector3(position.x, position.y - height/2, position.z)
        };

        // 연결점 객체 생성
        const connectionPoints = {};

        for (const [direction, pos] of Object.entries(points)) {
            const pointGeometry = new THREE.SphereGeometry(pointSize, 8, 8);
            const point = new THREE.Mesh(pointGeometry, pointMaterial);
            point.position.copy(pos);
            point.userData = {
                isConnectionPoint: true,
                direction: direction,
                parentId: id
            };

            // 씬에 추가
            groups.connectors.add(point);

            // 연결점 객체 저장
            connectionPoints[direction] = point;
        }

        // 연결점 맵에 저장
        connectionPointsMap[id] = connectionPoints;

        return connectionPoints;
    }

    // 요소 생성 함수
    function createElements() {
        // 모든 요소의 중심점 계산을 위한 변수
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;
        // 먼저 모든 요소의 위치를 파악하여 중심점 계산
        for (const [id, element] of Object.entries(diagramElements)) {
            if (id === 'title' || id === 'legend') continue;

            if (element.rect) {
                const x = element.rect.x - 500;
                const y = -element.rect.y + 400;
                const width = element.rect.width;
                const height = element.rect.height;

                minX = Math.min(minX, x);
                maxX = Math.max(maxX, x + width);
                minY = Math.min(minY, y - height);
                maxY = Math.max(maxY, y);
            }
        }

        // 중심점 계산
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;

        // 모든 요소 생성
        for (const [id, element] of Object.entries(diagramElements)) {
            let group;
            let color;
            let depth = 10; // 기본 깊이

            // 요소 유형에 따른 그룹 및 색상 설정
            if (id === 'title' || id === 'legend') {
                continue; // 제목과 범례는 3D로 변환하지 않음
            } else if (id.includes('plugin')) {
                group = groups.plugins;
                color = colors.plugins;
                depth = 15; // 플러그인 깊이
            } else if (id === 'dependencies') {
                group = groups.external;
                color = colors.external;
                depth = 8; // 외부 의존성 깊이
            } else if (id === 'aws-integration') {
                group = groups.integrations;
                color = colors.integrations;
                depth = 12; // 통합 깊이
            } else {
                group = groups.core;
                color = colors.core;
                depth = 20; // 코어 컴포넌트 깊이
            }

            // 요소 위치 및 크기 정보
            let x = 0, y = 0, width = 100, height = 50, rx = 0;

            if (element.rect) {
                x = element.rect.x - 500 - centerX; // 중앙 기준으로 조정
                y = -element.rect.y + 400 - centerY; // Y축 반전 및 조정
                width = element.rect.width;
                height = element.rect.height;
                rx = element.rect.rx || 0;
            }

            // 3D 박스 생성
            const boxGeometry = new THREE.BoxGeometry(width, height, depth);

            // 재질 생성
            const materials = [];

            // 앞면과 뒷면 - 메인 색상
            const mainMaterial = new THREE.MeshPhongMaterial({
                color: color.fill,
                transparent: true,
                opacity: 0.9,
                side: THREE.DoubleSide
            });

            // 테두리용 재질
            const edgeMaterial = new THREE.LineBasicMaterial({
                color: color.stroke,
                linewidth: element.rect?.strokeWidth || 1
            });

            // 모든 면에 동일한 재질 적용
            for (let i = 0; i < 6; i++) {
                materials.push(mainMaterial);
            }

            // 박스 메쉬 생성
            const box = new THREE.Mesh(boxGeometry, materials);
            box.position.set(x + width/2, y - height/2, 0);
            box.userData = { id, type: element.type, name: getElementName(element) };

            // 테두리 생성
            const edges = new THREE.EdgesGeometry(boxGeometry);
            const line = new THREE.LineSegments(edges, edgeMaterial);
            line.position.copy(box.position);

            // 텍스트 추가
            if (element.content) {
                element.content.forEach(item => {
                    if (item.type === 'text') {
                        // 텍스트 위치 계산
                        const textX = item.x - 500 - centerX; // 중앙 기준으로 조정
                        const textY = -item.y + 400 - centerY; // Y축 반전 및 조정

                        // 텍스트 내용에 따라 Z 위치 조정 (앞면에 표시)
                        const textZ = depth / 2 + 1; // 더 앞으로 나오도록 조정

                        // 텍스트 색상 결정
                        const textColor = item.fill === '#6c757d' ? colors.textSecondary : colors.text;

                        // 텍스트 크기 및 폰트 설정
                        const fontSize = item.fontSize * 0.6; // 텍스트 크기 증가
                        const fontWeight = item.fontWeight === 'bold' ? 'bold' : 'normal';

                        // 텍스트 생성 및 위치 설정
                        const textMesh = createText(item.text, fontSize, textColor, fontWeight);
                        textMesh.position.set(textX, textY, box.position.z + textZ);

                        // 텍스트가 항상 카메라를 향하도록 설정
                        textMesh.userData.isText = true;

                        // 텍스트 정렬 설정
                        if (item.textAnchor === 'middle') {
                            textMesh.geometry.center();
                        }

                        group.add(textMesh);
                    }
                });
            }

            // 그룹에 추가
            group.add(box);
            group.add(line);

            // 객체 맵에 저장
            objectMap[id] = box;

            // 연결점 생성
            createConnectionPoints(box, id);
        }
    }

    // 텍스트 생성 함수
    function createText(text, size, color, weight = 'normal') {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');

        // 텍스트 길이에 따라 캔버스 너비 조정
        const textLength = text.length;
        const canvasWidth = Math.max(512, textLength * 32);

        // 캔버스 크기 설정
        canvas.width = canvasWidth;
        canvas.height = 128;

        // 배경 설정 - 약간의 배경색 추가하여 가독성 향상
        context.fillStyle = 'rgba(255, 255, 255, 0.85)';
        context.fillRect(0, 0, canvas.width, canvas.height);

        // 테두리 추가
        context.strokeStyle = color.getStyle();
        context.lineWidth = 2;
        context.strokeRect(2, 2, canvas.width - 4, canvas.height - 4);

        // 텍스트 스타일 설정
        const fontWeight = weight;
        const fontSize = size * 3.5; // 해상도를 위해 3.5배 크기로 렌더링
        context.font = `${fontWeight} ${fontSize}px Arial`;
        context.fillStyle = color.getStyle();
        context.textAlign = 'center';
        context.textBaseline = 'middle';

        // 텍스트 그리기
        context.fillText(text, canvas.width / 2, canvas.height / 2);

        // 텍스처 생성
        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;
        texture.minFilter = THREE.LinearFilter; // 텍스트 선명도 향상
        texture.magFilter = THREE.LinearFilter;

        // 재질 생성
        const material = new THREE.MeshBasicMaterial({
            map: texture,
            transparent: true,
            opacity: 1,
            side: THREE.DoubleSide,
            depthTest: false // 항상 다른 객체 위에 렌더링
        });

        // 메쉬 생성 - 텍스트 길이에 따라 크기 조정
        const aspectRatio = canvas.width / canvas.height;
        const geometry = new THREE.PlaneGeometry(canvas.width / 5, canvas.height / 5);
        const mesh = new THREE.Mesh(geometry, material);

        return mesh;
    }

    // 가장 적합한 연결점 선택 함수 (가장 가까운 점 기준)
    function findBestConnectionPoints(sourceObj, targetObj) {
        // 소스와 타겟 객체의 연결점 가져오기
        const sourcePoints = connectionPointsMap[sourceObj.userData.id];
        const targetPoints = connectionPointsMap[targetObj.userData.id];

        if (!sourcePoints || !targetPoints) {
            console.error('연결점을 찾을 수 없습니다:', sourceObj.userData.id, targetObj.userData.id);
            return null;
        }

        // 가장 가까운 연결점 쌍 찾기
        let bestSourcePoint = null;
        let bestTargetPoint = null;
        let minDistance = Infinity;

        // 각 소스 연결점에 대해
        for (const [sourceDir, sourcePoint] of Object.entries(sourcePoints)) {
            // 각 타겟 연결점에 대해
            for (const [targetDir, targetPoint] of Object.entries(targetPoints)) {
                // 두 연결점 사이의 거리 계산
                const distance = sourcePoint.position.distanceTo(targetPoint.position);

                // 가장 짧은 거리를 가진 연결점 쌍 선택
                if (distance < minDistance) {
                    minDistance = distance;
                    bestSourcePoint = sourcePoint;
                    bestTargetPoint = targetPoint;
                }
            }
        }

        return {
            source: bestSourcePoint,
            target: bestTargetPoint
        };
    }

    // 연결선 생성 함수
    function createConnectors() {
        diagramConnectors.forEach((connector, index) => {
            const sourceObj = objectMap[connector.from];
            const targetObj = objectMap[connector.to];

            if (!sourceObj || !targetObj) return;

            // 연결선 색상 및 두께 설정
            const color = new THREE.Color(connector.stroke);
            const lineWidth = connector.strokeWidth * 0.5;

            // 가장 적합한 연결점 선택
            const connectionPoints = findBestConnectionPoints(sourceObj, targetObj);

            if (!connectionPoints) return;

            // 시작점과 끝점 위치
            const sourcePos = connectionPoints.source.position.clone();
            const targetPos = connectionPoints.target.position.clone();

            // 곡선 제어점 계산
            const distance = sourcePos.distanceTo(targetPos);
            const midPoint = new THREE.Vector3().addVectors(sourcePos, targetPos).multiplyScalar(0.5);

            // Z축 방향으로 곡선 생성
            const curveHeight = distance * 0.2;
            midPoint.z += curveHeight;

            // 3차 베지어 곡선 생성
            const curve = new THREE.QuadraticBezierCurve3(
                sourcePos,
                midPoint,
                targetPos
            );

            // 곡선 포인트 생성
            const points = curve.getPoints(50);
            const geometry = new THREE.BufferGeometry().setFromPoints(points);

            // 선 재질 생성
            const material = new THREE.LineBasicMaterial({
                color: color,
                linewidth: lineWidth,
                opacity: 0.6,
                transparent: true
            });

            // 선 객체 생성
            const line = new THREE.Line(geometry, material);

            // 연결선 정보 저장
            connections.push({
                line,
                sourceId: connector.from,
                targetId: connector.to,
                sourceObj,
                targetObj,
                sourcePoint: connectionPoints.source,
                targetPoint: connectionPoints.target
            });

            // 씬에 추가
            groups.connectors.add(line);
        });
    }

    // 객체 표면과 방향 벡터의 교차점 계산 함수
    function calculateIntersectionOffset(direction, size) {
        // 방향 벡터의 절대값
        const absDir = new THREE.Vector3(
            Math.abs(direction.x),
            Math.abs(direction.y),
            Math.abs(direction.z)
        );

        // 각 축별 반크기
        const halfSize = size.clone().multiplyScalar(0.5);

        // 각 축별 교차 거리 계산
        const distanceX = absDir.x > 0.0001 ? halfSize.x / absDir.x : Infinity;
        const distanceY = absDir.y > 0.0001 ? halfSize.y / absDir.y : Infinity;
        const distanceZ = absDir.z > 0.0001 ? halfSize.z / absDir.z : Infinity;

        // 가장 작은 거리 선택 (첫 교차점)
        const minDistance = Math.min(distanceX, distanceY, distanceZ);

        // 교차하는 면 결정
        let faceNormal = new THREE.Vector3();
        let faceIndex = 0; // 0: X축, 1: Y축, 2: Z축

        if (minDistance === distanceX) {
            // X축 면과 교차
            faceNormal.set(Math.sign(direction.x), 0, 0);
            faceIndex = 0;
        } else if (minDistance === distanceY) {
            // Y축 면과 교차
            faceNormal.set(0, Math.sign(direction.y), 0);
            faceIndex = 1;
        } else {
            // Z축 면과 교차
            faceNormal.set(0, 0, Math.sign(direction.z));
            faceIndex = 2;
        }

        // 교차점까지의 오프셋 계산 (방향 벡터 * 최소 거리)
        const intersectionOffset = direction.clone().multiplyScalar(minDistance);

        // 항상 옆면(X축 또는 Y축 면)을 통과하도록 강제 설정
        // Z축 면과 교차하는 경우, 가장 가까운 옆면으로 변경
        if (faceIndex === 2) {
            // Z축 면과 교차하는 경우, X축 또는 Y축 면으로 변경
            // X축과 Y축 중 더 가까운 면 선택
            if (distanceX < distanceY) {
                // X축 면이 더 가까움
                intersectionOffset.x = Math.sign(direction.x) * halfSize.x;
                intersectionOffset.y = direction.y * (halfSize.x / absDir.x);
                intersectionOffset.z = direction.z * (halfSize.x / absDir.x);
            } else {
                // Y축 면이 더 가까움
                intersectionOffset.x = direction.x * (halfSize.y / absDir.y);
                intersectionOffset.y = Math.sign(direction.y) * halfSize.y;
                intersectionOffset.z = direction.z * (halfSize.y / absDir.y);
            }
        }

        return intersectionOffset;
    }

    // 요소 이름 추출 함수
    function getElementName(element) {
        if (!element.content) return '';

        // 첫 번째 텍스트 요소 찾기
        for (const item of element.content) {
            if (item.type === 'text' && !item.fill) {
                return item.text;
            }
        }

        return '';
    }

    // 창 크기 변경 이벤트 핸들러
    function onWindowResize() {
        const width = container.clientWidth;
        const height = container.clientHeight;

        camera.aspect = width / height;
        camera.updateProjectionMatrix();

        renderer.setSize(width, height);
    }

    // 마우스 이동 이벤트 핸들러
    function onMouseMove(event) {
        // 마우스 좌표 계산
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        // 레이캐스팅
        raycaster.setFromCamera(mouse, camera);

        // 모든 객체 그룹에서 교차 검사
        const allObjects = [];
        Object.values(groups).forEach(group => {
            group.children.forEach(child => {
                if (child.type === 'Mesh' && child.userData && child.userData.id) {
                    allObjects.push(child);
                }
            });
        });

        const intersects = raycaster.intersectObjects(allObjects);

        // 커서 스타일 및 툴팁 업데이트
        if (intersects.length > 0) {
            const object = intersects[0].object;

            if (object.userData && object.userData.id) {
                container.style.cursor = 'pointer';

                // 툴팁 표시
                if (object.userData.name) {
                    tooltip.textContent = object.userData.name;
                    tooltip.style.opacity = '1';
                    tooltip.style.left = event.clientX + 10 + 'px';
                    tooltip.style.top = event.clientY + 10 + 'px';
                }

                // 호버 효과
                if (hoveredObject && hoveredObject !== object) {
                    resetHoverEffect(hoveredObject);
                }

                hoveredObject = object;
                applyHoverEffect(object);
            }
        } else {
            container.style.cursor = 'grab';
            tooltip.style.opacity = '0';

            // 호버 효과 제거
            if (hoveredObject) {
                resetHoverEffect(hoveredObject);
                hoveredObject = null;
            }
        }
    }

    // 마우스 클릭 이벤트 핸들러
    function onMouseClick(event) {
        // 레이캐스팅
        raycaster.setFromCamera(mouse, camera);

        // 모든 객체 그룹에서 교차 검사
        const allObjects = [];
        Object.values(groups).forEach(group => {
            group.children.forEach(child => {
                if (child.type === 'Mesh' && child.userData && child.userData.id) {
                    allObjects.push(child);
                }
            });
        });

        const intersects = raycaster.intersectObjects(allObjects);

        if (intersects.length > 0) {
            const object = intersects[0].object;

            if (object.userData && object.userData.id) {
                // 클릭된 객체 포커스
                focusOnObject(object);
            }
        }
    }

    // 호버 효과 적용 함수
    function applyHoverEffect(object) {
        // 객체 크기 약간 확대
        object.scale.set(1.05, 1.05, 1.05);

        // 관련 연결선 강조
        highlightConnections(object.userData.id);
    }

    // 호버 효과 제거 함수
    function resetHoverEffect(object) {
        // 객체 크기 원래대로
        object.scale.set(1, 1, 1);

        // 연결선 효과 제거
        resetConnectionsHighlight();
    }

    // 연결선 강조 함수
    function highlightConnections(id) {
        connections.forEach(conn => {
            if (conn.sourceId === id || conn.targetId === id) {
                // 연결선 불투명도 증가
                conn.line.material.opacity = 1;

                // 연결점 강조 (크기 증가 및 색상 변경)
                if (conn.sourcePoint) {
                    conn.sourcePoint.scale.set(1.5, 1.5, 1.5);
                    conn.sourcePoint.material.color.set(0xff0000); // 빨간색으로 변경
                    conn.sourcePoint.material.opacity = 1;
                }

                if (conn.targetPoint) {
                    conn.targetPoint.scale.set(1.5, 1.5, 1.5);
                    conn.targetPoint.material.color.set(0xff0000); // 빨간색으로 변경
                    conn.targetPoint.material.opacity = 1;
                }

                // 연결된 다른 객체도 약간 강조
                const otherObj = conn.sourceId === id ? conn.targetObj : conn.sourceObj;
                otherObj.scale.set(1.02, 1.02, 1.02);
            }
        });
    }

    // 연결선 강조 제거 함수
    function resetConnectionsHighlight() {
        connections.forEach(conn => {
            // 연결선 불투명도 원래대로
            conn.line.material.opacity = 0.6;

            // 연결점 원래대로
            if (conn.sourcePoint) {
                conn.sourcePoint.scale.set(1, 1, 1);
                conn.sourcePoint.material.color.set(0x007bff); // 원래 색상으로 복원
                conn.sourcePoint.material.opacity = 0.7;
            }

            if (conn.targetPoint) {
                conn.targetPoint.scale.set(1, 1, 1);
                conn.targetPoint.material.color.set(0x007bff); // 원래 색상으로 복원
                conn.targetPoint.material.opacity = 0.7;
            }

            // 연결된 객체들 크기 원래대로
            if (conn.sourceObj !== hoveredObject) {
                conn.sourceObj.scale.set(1, 1, 1);
            }

            if (conn.targetObj !== hoveredObject) {
                conn.targetObj.scale.set(1, 1, 1);
            }
        });
    }

    // 객체에 포커스 함수
    function focusOnObject(object) {
        // 카메라 이동 애니메이션
        const targetPosition = object.position.clone();
        const distance = object.geometry.parameters.width * 2;

        // 카메라 위치 계산
        const cameraPosition = new THREE.Vector3();
        cameraPosition.copy(targetPosition);
        cameraPosition.z += distance;

        // 애니메이션 설정
        const duration = 1000; // 1초
        const startTime = Date.now();
        const startPosition = camera.position.clone();

        // 애니메이션 함수
        function animateCamera() {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // 이징 함수 (부드러운 이동)
            const easeProgress = 1 - Math.pow(1 - progress, 3);

            // 카메라 위치 보간
            camera.position.lerpVectors(startPosition, cameraPosition, easeProgress);

            // 카메라가 객체를 바라보도록 설정
            controls.target.copy(targetPosition);
            controls.update();

            // 애니메이션 완료 여부 확인
            if (progress < 1) {
                requestAnimationFrame(animateCamera);
            }
        }

        // 애니메이션 시작
        animateCamera();
    }

    // 카메라 초기화 함수
    function resetCamera() {
        // 초기 카메라 위치로 애니메이션
        const targetPosition = new THREE.Vector3(0, 400, 1000);
        const targetLookAt = new THREE.Vector3(0, 0, 0);

        // 애니메이션 설정
        const duration = 1000; // 1초
        const startTime = Date.now();
        const startPosition = camera.position.clone();
        const startTarget = controls.target.clone();

        // 애니메이션 함수
        function animateReset() {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // 이징 함수 (부드러운 이동)
            const easeProgress = 1 - Math.pow(1 - progress, 3);

            // 카메라 위치 보간
            camera.position.lerpVectors(startPosition, targetPosition, easeProgress);

            // 카메라 타겟 보간
            controls.target.lerpVectors(startTarget, targetLookAt, easeProgress);
            controls.update();

            // 애니메이션 완료 여부 확인
            if (progress < 1) {
                requestAnimationFrame(animateReset);
            }
        }

        // 애니메이션 시작
        animateReset();
    }

    // 애니메이션 함수
    function animate() {
        requestAnimationFrame(animate);

        // 컨트롤 업데이트
        controls.update();

        // 텍스트가 항상 카메라를 향하도록 업데이트
        Object.values(groups).forEach(group => {
            group.children.forEach(child => {
                if (child.userData && child.userData.isText) {
                    child.lookAt(camera.position);
                }
            });
        });

        // 렌더링
        renderer.render(scene, camera);
    }

    // 초기화 실행
    init();
});
