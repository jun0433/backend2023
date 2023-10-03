#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <string.h>
#include <unistd.h>

#include <iostream>
#include <string>

using namespace std;

int main()
{
  int s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
  if (s < 0)
    return 1;

  string buf = "Hello World";

  struct sockaddr_in sin;
  memset(&sin, 0, sizeof(sin));
  sin.sin_family = AF_INET;
  sin.sin_addr.s_addr = INADDR_ANY;
  sin.sin_port = htons(20000 + 5019);
  if (bind(s, (struct sockaddr *)&sin, sizeof(sin)) < 0)
  {
    cerr << strerror(errno) << endl;
    return 0;
  }

  while (true)
  {

    int numBytes = sendto(s, buf.c_str(), buf.length(), 0, (struct sockaddr *)&sin, sizeof(sin));
    cout << "Sent: " << numBytes << endl;

    char buf2[65536];
    memset(&sin, 0, sizeof(sin));
    socklen_t sin_size = sizeof(sin);
    numBytes = recvfrom(s, buf2, sizeof(buf2), 0, (struct sockaddr *)&sin, &sin_size);
    cout << "Recevied: " << numBytes << endl;
    cout << "From " << inet_ntoa(sin.sin_addr) << endl;
  }

  close(s);

  return 0;
}
