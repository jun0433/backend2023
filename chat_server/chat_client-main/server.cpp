#include <iostream>
#include <thread>
#include <mutex>

using namespace std;

void join() {
  cout << "메시지 작업 쓰레드 # 생성" << endl;
}

void shutdown(thread a){
  a.join();
}



int main(){

  thread t1(join);
  thread t2(join);



  string command;

  while(command != "/shutdown"){
    cin >> command;
  }
  
  t1.join();
  t2.join();

  return 0;
}