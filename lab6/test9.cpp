#include <chrono>
#include <iostream>
#include <mutex>
#include <thread>

using namespace std;

int sum = 0;
mutex m;
mutex m2;

void f() {
  for (int i = 0; i < 10 * 1000 * 1000; ++i) {
    ++sum;
  }
}


int main() {
  thread t(f);
  for (int i = 0; i < 10 * 1000 * 1000; ++i) {
    m.lock();
    m2.lock();
    ++sum;
    m.unlock();
    m2.unlock();
  }
  t.join();
  cout << "Sum: " << sum << endl;
}
