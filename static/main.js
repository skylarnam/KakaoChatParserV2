// 파일 업로드 처리
document.getElementById('csvFile').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('file', file);
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error uploading file: ' + data.error);
            }
        });
    }
});

// 업로드 섹션 표시
function showUploadSection() {
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('dashboardContent').style.display = 'none';
}

// 월간 통계 차트
function loadMonthlyStats() {
    fetch('/api/monthly_stats')
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('monthlyStats').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(item => item.user),
                    datasets: [{
                        label: '메시지 수',
                        data: data.map(item => item.count),
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '메시지 수'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '사용자 (상위 10명)'
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: '월간 채팅 통계 (상위 10명)',
                            padding: {
                                top: 10,
                                bottom: 30
                            }
                        },
                        legend: {
                            display: false
                        }
                    }
                }
            });
        });
}

// 채팅 추이 차트
function loadChatTrend() {
    fetch('/api/chat_trend')
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('chatTrend').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(item => item.date),
                    datasets: [{
                        label: '일일 메시지 수',
                        data: data.map(item => item.count),
                        borderColor: 'rgba(75, 192, 192, 1)',
                        tension: 0.1,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '메시지 수'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '날짜'
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: '일일 채팅 추이',
                            padding: {
                                top: 10,
                                bottom: 30
                            }
                        }
                    }
                }
            });
        });
}

// 사용자 목록 로드 및 드롭다운 채우기
function loadUserList() {
    fetch('/api/users')
        .then(response => response.json())
        .then(users => {
            const select = document.getElementById('userSelect');
            select.innerHTML = '<option value="">사용자 선택</option>';
            users.sort().forEach(user => {
                const option = document.createElement('option');
                option.value = user;
                option.textContent = user;
                select.appendChild(option);
            });
        });
}

// 사용자별 통계 로드
function loadUserStats(username) {
    const infoDiv = document.getElementById('userStatsInfo');
    if (!username) {
        infoDiv.textContent = '';
        return;
    }
    fetch(`/api/user_stats/${encodeURIComponent(username)}`)
        .then(response => response.json())
        .then(data => {
            infoDiv.textContent = `${username}님의 월간 메시지 수: ${data.total_messages}`;
        });
}

document.getElementById('userSelect').addEventListener('change', function(e) {
    loadUserStats(e.target.value);
});

// 비활성 사용자 버튼 active 관리
function setActiveInactiveBtn(days) {
    ['30', '60', '90'].forEach(d => {
        document.getElementById('btn-inactive-' + d).classList.remove('active');
    });
    if (days) {
        document.getElementById('btn-inactive-' + days).classList.add('active');
    }
}

// 비활성 사용자 로드 (일수 기준)
function loadInactiveUsers(days) {
    setActiveInactiveBtn(days);
    fetch(`/api/inactive_users/${days}`)
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('inactiveUsers');
            if (data.length === 0) {
                container.innerHTML = '<span class="text-muted">비활성 사용자가 없습니다.</span>';
            } else {
                container.innerHTML = data
                    .map(user => `<span class=\"badge-outline-primary\">${user}</span>`)
                    .join('');
            }
            container.style.display = 'block';
        });
}

// 비활성 사용자 로드 (날짜 범위 기준)
function loadInactiveUsersByDate(event) {
    event.preventDefault();
    setActiveInactiveBtn(null);
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value || new Date().toISOString().split('T')[0];
    const errorElement = document.getElementById('dateError');
    fetch(`/api/inactive_users_by_date?start_date=${startDate}&end_date=${endDate}`)
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('inactiveUsers');
            if (data.error) {
                errorElement.textContent = data.error;
                errorElement.style.display = 'block';
                container.style.display = 'none';
                return;
            }
            errorElement.style.display = 'none';
            if (data.length === 0) {
                container.innerHTML = '<span class="text-muted">비활성 사용자가 없습니다.</span>';
            } else {
                container.innerHTML = data
                    .map(user => `<span class=\"badge-outline-primary\">${user}</span>`)
                    .join('');
            }
            container.style.display = 'block';
        })
        .catch(error => {
            errorElement.textContent = '데이터를 불러오는 중 오류가 발생했습니다.';
            errorElement.style.display = 'block';
            document.getElementById('inactiveUsers').style.display = 'none';
        });
}

// 초기 데이터 로드
const hasData = JSON.parse(document.getElementById('dashboardContent') ? 'true' : 'false');
if (typeof hasData !== 'undefined' && hasData) {
    document.getElementById('uploadSection').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';
    loadMonthlyStats();
    loadChatTrend();
    loadUserList();
    loadInactiveUsers(30);
    setActiveInactiveBtn(30);
}

// 비활성 사용자 복사 기능
function copyInactiveUsers() {
    const container = document.getElementById('inactiveUsers');
    const badges = container.getElementsByClassName('badge-outline-primary');
    
    if (badges.length === 0) {
        alert('복사할 비활성 사용자가 없습니다.');
        return;
    }

    // 현재 활성화된 버튼 확인
    const activeButton = document.querySelector('.btn-group .btn.active');
    let dateRangeText;
    
    if (activeButton) {
        // 30/60/90일 버튼이 활성화된 경우
        const days = parseInt(activeButton.id.split('-')[2]);
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - days);
        
        dateRangeText = `[${startDate.toISOString().split('T')[0]} ~ ${endDate.toISOString().split('T')[0]} 사이의 비활성 사용자]`;
    } else {
        // 날짜 선택기를 사용한 경우
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value || new Date().toISOString().split('T')[0];
        dateRangeText = `[${startDate} ~ ${endDate} 사이의 비활성 사용자]`;
    }

    let text = dateRangeText + '\n';
    // 사용자 목록을 배열로 변환하고 정렬
    const userList = Array.from(badges)
        .map(badge => badge.textContent)
        .sort((a, b) => {
            // 영어와 한글 구분을 위한 정규식
            const isEnglishA = /^[a-zA-Z]/.test(a);
            const isEnglishB = /^[a-zA-Z]/.test(b);
            
            // 영어가 한글보다 먼저 오도록 정렬
            if (isEnglishA && !isEnglishB) return -1;
            if (!isEnglishA && isEnglishB) return 1;
            
            // 같은 종류(영어/한글)끼리는 알파벳 순으로 정렬
            return a.localeCompare(b, 'ko');
        });
    
    // 정렬된 목록을 텍스트로 변환
    text += userList.join('\n');

    navigator.clipboard.writeText(text).then(() => {
        alert('비활성 사용자 목록이 클립보드에 복사되었습니다.');
    }).catch(err => {
        console.error('클립보드 복사 실패:', err);
        alert('클립보드 복사에 실패했습니다.');
    });
} 