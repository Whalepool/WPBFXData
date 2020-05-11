import coloredlogs, logging
import json, time, zmq, sys, os

logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG', logger=logger)


class ZmqRelay(  ):


    def __init__(self, topic, server=False, ZMQ_PUBLISH_TO_PORT=5557, ZMQ_RECEIVE_FROM_TO_PORT=5558, singular=False ):

        self.send_topic    = topic+'_request'
        self.recieve_topic = topic+'_reply' 
        if server == True:
            self.send_topic = topic+'_reply' 
            self.recieve_topic = topic+'_request' 
        if singular == True:
            self.send_topic = topic 
            self.recieve_topic = topic 


        self.context = zmq.Context()
        self.sender = self.context.socket(zmq.PUB)
        self.sender.connect('tcp://127.0.0.1:{}'.format(ZMQ_PUBLISH_TO_PORT))

        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.connect('tcp://127.0.0.1:{}'.format(ZMQ_RECEIVE_FROM_TO_PORT))
        self.receiver.setsockopt_string(zmq.SUBSCRIBE, self.recieve_topic)

        time.sleep(0.1)

    def set_recv_timeout(self, miliseconds=-1):
        self.receiver.setsockopt(zmq.RCVTIMEO, miliseconds)

    def mogrify(self, topic, msg):
        """ json encode the message and prepend the topic """
        return topic + ' ' + json.dumps(msg,  default=str)

    def demogrify(self, topicmsg):
        """ Inverse of mogrify() """
        json0 = topicmsg.find('[')
        json1 = topicmsg.find('{')

        start = json0
        if (json1 > 0):
            if (json0 > 0):
                if (json1 < json0):
                    start = json1
            else:
                start = json1

        topic = topicmsg[0:start].strip()
        msg = json.loads(topicmsg[start:])

        return topic, msg   #


    def send_msg( self, msg ):
        logger.info('Sending: '+str(msg))
        data = self.mogrify(self.send_topic, msg )
        self.sender.send_string(data)
