run:
	docker build -t cryptoscreener .
	docker run --name cryptoscreener -d -p 5000:5000 cryptoscreener

rerun:
	docker rm --force cryptoscreener
	docker build -t cryptoscreener .
	docker run --name cryptoscreener -d -p 5000:5000 cryptoscreener

stop:
	docker stop cryptoscreener
	docker rm cryptoscreener

clean:
	docker rmi cryptoscreener
