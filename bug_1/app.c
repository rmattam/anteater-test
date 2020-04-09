// isend_irecv
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#define TAG 13

int main(int argc, char *argv[]) {
   int myid, numprocs, left, right;
    int buf, buff2 = 5;
    MPI_Request request, request2, request3, request4;
    MPI_Status status1,status2,status3,status4;

    MPI_Init(&argc,&argv);
    MPI_Comm_size(MPI_COMM_WORLD, &numprocs);
    MPI_Comm_rank(MPI_COMM_WORLD, &myid);

    if(myid == 1){
        usleep(300000);
    }

    if(myid == 3){
        usleep(5000000);
    }

    if(myid == 0){
    MPI_Irecv(&buf, 1, MPI_INT, 1, 123, MPI_COMM_WORLD, &request);
    usleep(300000);
    MPI_Isend(&buff2, 1, MPI_INT, 1, 123, MPI_COMM_WORLD, &request2);
    usleep(300000);
    MPI_Wait(&request2, &status3);
    usleep(600000);
    MPI_Wait(&request, &status4);
    usleep(300000);
    }
    if(myid == 1){
    MPI_Irecv(&buf, 1, MPI_INT, 0, 123, MPI_COMM_WORLD, &request3);
    usleep(300000);
    MPI_Isend(&buff2, 1, MPI_INT, 0, 123, MPI_COMM_WORLD, &request4);
    usleep(300000);
    MPI_Wait(&request3, &status1);
    usleep(600000);
    MPI_Wait(&request4, &status2);
    usleep(300000);
    }
    MPI_Barrier(MPI_COMM_WORLD);
    MPI_Finalize();
    return 0;
}
