
	var _DEFAULT_COOKIE_TIME_ = 31536000;


	/*
		cookie util
	*/
	var cookies = {
		setCookie: function (name, value, tm) {
			var date = "";
			var expires = "";
			if (tm) {
				date = new Date();
				date.setTime(date.getTime()+(tm*60*1000));
				expires = "; expires="+ date.toGMTString();
			}
			document.cookie = name+"="+value+expires+"; path=/";
		},
		getCookie: function (name) {
			var nameEQ = name + "=";
			var ca = document.cookie.split(';');

			for(var i=0;i < ca.length;i++) {
				var c = ca[i];
				while (c.charAt(0)==' ') c = c.substring(1,c.length);
				if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
			}
			return null;
		},
		destoryCookie: function (name) {
			this.setCookie(name,"", -1);
		}
	};

	function convertOrdinalNumber(n) {
    n = parseInt(n, 10);
    const suffix = ['th', 'st', 'nd', 'rd'];
    const mod100 = n % 100;

    return n+(suffix[(mod100-20)%10] || suffix[mod100] || suffix[0]);
	}

	//get url param
	function getParameter( name ) {
	  name = name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");
	  var regexS = "[\\?&]"+name+"=([^&#]*)";
	  var regex = new RegExp( regexS );
	  var results = regex.exec( window.location.href );
	  if( results == null )
		return "";
	  else
		return results[1];
	}


	//소수점 지정 및 콤마
	function tofix(num, check) {
		var fixedNum = Math.round((num * 100)) / 100;
		var regexp = /\B(?=(\d{3})+(?!\d))/g;
		if(check){
			if(fixedNum % 1 == 0){
				return fixedNum.toString().replace(regexp, ',') + ".00";
			}else if((fixedNum*10 % 1) == 0){
				return fixedNum.toString().replace(regexp, ',') + "0";
			}
		}

		return fixedNum.toString().replace(regexp, ',');
	}

	//소수점 지정 및 콤마
	function tofixOne(num, check) {
		var fixedNum = Math.round((num * 10)) / 10;
		var regexp = /\B(?=(\d{3})+(?!\d))/g;
		if(check){
			if(fixedNum % 1 == 0){
				return fixedNum.toString().replace(regexp, ',') + ".0";
			}
		}

		return fixedNum.toString().replace(regexp, ',');
	}


//---------------------------- 날짜 함수 -------------------------------------------/
	/**
	 * [년도, 년주차, 년도+주차] 가져오기
	 * @returns {*[]}
	 */
	Date.prototype.getWeekOfYear = function() {
		var date = new Date(this.getTime());
		date.setHours(0, 0, 0, 0);
		// Thursday in current week decides the year.
		date.setDate(date.getDate() + 3 - (date.getDay() + 6) % 7);
		// January 4 is always in week 1.
		var week1 = new Date(date.getFullYear(), 0, 4);
		// Adjust to Thursday in week 1 and count number of weeks from date to week1.
		var year = date.getFullYear();
		var weekNum = (1 + Math.round(((date.getTime() - week1.getTime()) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7));
		return [year, weekNum, year + '' + (weekNum.length === 1 ? "0" + weekNum : weekNum)];
	};

	var getWeekOfYear_myDate = function(date) {
		date.setHours(0, 0, 0, 0);
		// Thursday in current week decides the year.
		date.setDate(date.getDate() + 3 - (date.getDay() + 6) % 7);
		// January 4 is always in week 1.
		var week1 = new Date(date.getFullYear(), 0, 4);
		// Adjust to Thursday in week 1 and count number of weeks from date to week1.
		var year = date.getFullYear();
		var weekNum = (1 + Math.round(((date.getTime() - week1.getTime()) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7));
		return [year, weekNum, year + '' + (weekNum.length === 1 ? "0" + weekNum : weekNum)];
	};


	/**
	 * 년 주차기준 시작 년-월-일 가져오기
	 * @returns {*[]}
	 */
	var getDayOfWeekNum = function(weekNum) {
		var y = weekNum.substr(0, 4);
		var w = weekNum.substr(4, 6);

		if(w.substring(4,6).length === 1){
			w ="0" + w.substring(4,5);
		}

		//pvca 2020 53 주까지 있어서 아래코드 임시로 처리
		w = y=='2021' && w=='01' ? 2 : (y=='2021' || y=='2022') ? parseInt(w)+1 : w;
	console.log('getDayOfWeekNum ooooooo --> '+ w );

		var d = (1 + (w - 1) * 7);
		var day = new Date(y, 0, d);
		console.log('tvr.date.init -> ddddd :' + d);

		if(day.getDay() !== 1){
			for(var i=1; i < 7; i++){
				day = new Date(y, 0, d-i);
				if(day.getDay() === 1){
					break;
				}
			}
		}

		var month = day.getMonth() + 1;
		month = month > 9 ? month : '0' + month;


		return day.getFullYear() + '-' + month + '-' + (day.getDate() < 10 ? '0' + day.getDate() : day.getDate());
	};

	var getEndDayOfWeekNum = function(weekNum) {
		var y = weekNum.substr(0, 4);
		var w = weekNum.substr(4, 6);

		if(w.substring(4,6).length === 1){
			w ="0" + w.substring(4,5);
		}

		//pvca 2020 53 주까지 있어서 아래코드 임시로 처리
		w = y=='2021' && w=='01' ? 2 : (y=='2021' || y=='2022') ? parseInt(w)+1 : w;

		var d = (7 + (w - 1) * 7);
		var day = new Date(y, 0, d);

		if(day.getDay() !== 0){
			for(var i=1; i < 7; i++){
				day = new Date(y, 0, d-i);
				if(day.getDay() === 0){
					break;
				}
			}
		}

		var month = day.getMonth() + 1;
		month = month > 9 ? month : '0' + month;

		return day.getFullYear() + '-' + month + '-' + (day.getDate() < 10 ? '0' + day.getDate() : day.getDate());
	};


	/**
	 * 년, 월, 월주차 가져오기
	 * @returns {*[]}
	 */
	Date.prototype.getWeekOfMonth = function() {
		var year = this.getFullYear();
		var month = this.getMonth() + 1;
		var weekNum = this.getWeekNum_month();
		//console.log(weekNum);
		if (weekNum === 0) {
			if (month === 1) {
				year -= 1;
				month = 11;
			} else {
				month -= 1;
			}
			weekNum = (new Date(year, month, 0)).getWeekNum_month();
		}
		else if (weekNum === -1) {
			if (month === 12) {
				year += 1;
				month = 1;
			} else {
				month += 1;
			}
			weekNum = 1;
			//console.log("여기 들어오냐 설마");
		}

		return [year, month, weekNum];
	};


	/**
	 * 월 기준 주차 ( 0 : 전월 마지막주차, -1 : 다음달 첫번째 주차)
	 * @returns {number}
	 */
	Date.prototype.getWeekNum_month = function() {
		var startWeekArray = Array(2, 0, 0, 0, 0, 4, 3); // 일, 월, 화, 수, 목, 금, 토

		var month = this.getMonth();
		var year = this.getFullYear();

		var firstWeekday = startWeekArray[new Date(year, month, 1).getDay()];
		var lastDateOfMonth = new Date(year, month + 1, 0).getDate();
		var lastWeekday = new Date(year, month, lastDateOfMonth).getDay();

		//console.log("lastDateOfMonth : " + lastDateOfMonth);
		//console.log("firstWeekday : " + firstWeekday);
		//console.log("lastWeekday : " + lastWeekday);

		var offsetDate = this.getDate() - firstWeekday;
		//console.log("this : " + this)
		//console.log("this.getDate() : " + this.getDate());
		//console.log("offsetDate : " + offsetDate);
		var index = 1; // start index at 0 or 1, your choice
		var weeksInMonth = index + Math.ceil((lastDateOfMonth + firstWeekday - 7) / 7);
		var week = index + Math.floor(offsetDate / 7);
		//console.log("weeksInMonth : " + weeksInMonth);
		//console.log("week : " + week);

		if (week == weeksInMonth && lastWeekday < 1) week = -1;

		return week;
	};


	/*
	해당 날짜의 월 주차 구하기
	2019.01.02
	*/
	Date.prototype.getWeek = function(start)
	{
			//Calcing the starting point
		start = start || 0;
		var today = new Date(this.setHours(0, 0, 0, 0));
		var day = today.getDay() - start;
		var date = today.getDate() - day;

			// Grabbing Start/End Dates
		var StartDate = new Date(today.setDate(date + 1));
		var EndDate = new Date(today.setDate(date + 5));
		return [StartDate, EndDate];
	}



	/**
	 * 기준년도 부터 현재까지 년도 목록 가져오기
	 */
	function getYearList (fullYear) {
		var list = [];
		var year = moment(fullYear + '-01-01');
		var currentYear = moment().format('YYYY');
		var nextYear = fullYear;

		while (nextYear !== currentYear) {
			nextYear = year.add(1, 'year').format('YYYY');
			list.push(nextYear);
		}

		return list;
	}


	//pvca	2016.01.20
	function strDateFormats(fm, v)  {
		if(v == undefined)  return;

		return v.substring(0,4) +fm+ v.substring(4,6) +fm+v.substring(6,8);
	}


	//pvca	2016.01.20
	function strTimeFormats(v)  {
		if(v == undefined)  return;

		return v.substring(0,2) +':'+ v.substring(2,4) +':'+v.substring(4,6);
	}

	function nl2br(str){
		if(str == undefined)  return;

		return str.replace(/\n/g, "<br />");
	}


	//5자리 주차번호 수정 함수 2019 01 08 김동완
	function wcd_check(data){
		if(data.length < 6){
			data = data.substring(0,4) + "0" + data.substring(4);
		}
		return data;
	}


	// 목요일 기준 주차 구하기
	function weekNumberByThurFnc(paramDate) {
		var year = paramDate.getFullYear();
		var month = paramDate.getMonth();
		var date = paramDate.getDate();

		// 인풋한 달의 첫 날과 마지막 날의 요일
		var firstDate = new Date(year, month, 1);
		var lastDate = new Date(year, month+1, 0);
		var firstDayOfWeek = firstDate.getDay() === 0 ? 7 : firstDate.getDay();
		var lastDayOfweek = lastDate.getDay();

		// 인풋한 달의 마지막 일
		var lastDay = lastDate.getDate();

		// 첫 날의 요일이 금, 토, 일요일 이라면 true
		var firstWeekCheck = firstDayOfWeek === 5 || firstDayOfWeek === 6 || firstDayOfWeek === 7;
		// 마지막 날의 요일이 월, 화, 수라면 true
		var lastWeekCheck = lastDayOfweek === 1 || lastDayOfweek === 2 || lastDayOfweek === 3;

		// 해당 달이 총 몇주까지 있는지
		var lastWeekNo = Math.ceil((firstDayOfWeek - 1 + lastDay) / 7);

		// 날짜 기준으로 몇주차 인지
		var weekNo = Math.ceil((firstDayOfWeek - 1 + date) / 7);

		// 인풋한 날짜가 첫 주에 있고 첫 날이 월, 화, 수로 시작한다면 'prev'(전달 마지막 주)
		if(weekNo === 1 && firstWeekCheck) weekNo = 'prev';
		// 인풋한 날짜가 마지막 주에 있고 마지막 날이 월, 화, 수로 끝난다면 'next'(다음달 첫 주)
		else if(weekNo === lastWeekNo && lastWeekCheck) weekNo = 'next';
		// 인풋한 날짜의 첫 주는 아니지만 첫날이 월, 화 수로 시작하면 -1;
		else if(firstWeekCheck) weekNo = weekNo -1;

		return weekNo;
	};

	//특정 날짜의 월 주차번호 가져우기
	function weekNumberByMonth(dateFormat) {
		var inputDate = new Date(dateFormat);

		//pvca 2020 53 주까지 있어서 아래코드 임시로 처리
		//w = y=='2021' && w=='01' ? 2 : (y=='2021') ? parseInt(w)+1 : w;

		// 인풋의 년, 월
		var year = inputDate.getFullYear();
		var month = inputDate.getMonth() + 1;


		// 목요일 기준 주차 구하기

		// 목요일 기준의 주차
		var weekNo = weekNumberByThurFnc(inputDate);

		// 이전달의 마지막 주차일 떄
		if(weekNo === 'prev') {
			// 이전 달의 마지막날
			var afterDate = new Date(year, month-1, 0);
			year = month === 1 ? year - 1 : year;
			month = month === 1 ? 12 : month - 1;
			weekNo = weekNumberByThurFnc(afterDate);
		}

		// 다음달의 첫 주차일 때
		if(weekNo === 'next') {
			year = month === 12 ? year + 1 : year;
			month = month === 12 ? 1 : month + 1;
			weekNo = 1;
		}

		res = [];
		res.push(year);
		res.push(month);
		res.push(weekNo);


	  return res;
	}




	//pvca  2021.11.02
	function comma(str) {
		str = String(str);
		return str.replace(/(\d)(?=(?:\d{3})+(?!\d))/g, '$1,');
	}

	//pvca  2021.11.02
	//콤마풀기
	function uncomma(str) {
		str = String(str);
		return str.replace(/[^\d]+/g, '');
	}
