.PHONY: clean

clls_pb2.py: clls.proto
	protoc clls.proto --python_out=.

clean:
	rm -f clls_pb2.py*

